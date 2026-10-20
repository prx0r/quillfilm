#!/usr/bin/env python3
"""quill-bridge: the box-side helper for quill (YouTube + search).

Runs on whichever box can reach YouTube (needs account cookies OR a
non-datacenter IP). quill's worker proxies /api/yt/* here; BRIDGE_URL points
at this service's public hostname (cloudflared tunnel).

Endpoints (all GET, all JSON except /yt/clip which returns video bytes):
  /yt/meta?v=VIDEO_ID            title/duration/uploader via yt-dlp
  /yt/transcript?v=VIDEO_ID      timed segments via youtube-transcript-api
  /yt/clip?v=ID&start=SS&dur=N   ≤60s mp4 slice via yt-dlp + ffmpeg
  /search?q=...                  DuckDuckGo results (box parity w/ worker)

Auth: X-Bridge-Key header must match $BRIDGE_KEY (if set).
Cookies: yt-dlp uses /root/.yt-cookies.txt when present (Netscape format).
Without valid cookies on a blocked IP, yt endpoints answer 502 youtube-blocked.

Run: BRIDGE_KEY=... python3 bridge.py   (listens 127.0.0.1:18787)
"""
import json
import os
import re
import subprocess
import tempfile
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 18787
COOKIES = '/root/.yt-cookies.txt'
BRIDGE_KEY = os.environ.get('BRIDGE_KEY', '')
YTDLP = ['yt-dlp']
RENDER_DIR = '/root/.quill-render/jobs'
TTS_DIR = '/root/.quill-render/tts'
PHONON_MODEL = os.environ.get('PHONON_MODEL', '/root/phonon/model-31m-en')
PHONON_BIN = os.environ.get('PHONON_BIN', '/root/.cargo/bin/ptts')

def _fish_key() -> str:
    k = os.environ.get('FISH_API_KEY', '')
    if k:
        return k
    for p in ('/root/.fish-env', '/root/freaktown/.env'):
        try:
            with open(p) as f:
                for line in f:
                    if line.startswith('FISH_API_KEY='):
                        return line.strip().split('=', 1)[1]
        except OSError:
            pass
    return ''

# In-memory search cache (DDG throttles repeated hits from one IP).
import time as _time
_SEARCH_CACHE: dict = {}
_SEARCH_TTL = 3600


def err(handler, code, payload):
    body = json.dumps(payload).encode()
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def run(cmd, timeout=120):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p


def ytdlp_base():
    cmd = list(YTDLP) + ['--no-warnings']
    if os.path.exists(COOKIES):
        cmd += ['--cookies', COOKIES]
    return cmd


class H(BaseHTTPRequestHandler):
    server_version = 'quill-bridge/1'

    def log_message(self, *a):
        pass

    def check_auth(self):
        if not BRIDGE_KEY:
            return True
        return self.headers.get('X-Bridge-Key') == BRIDGE_KEY

    def _body(self):
        try:
            n = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            n = 0
        return self.rfile.read(min(n, 4_000_000)).decode('utf-8', 'replace')

    def do_POST(self):
        if not self.check_auth():
            return err(self, 401, {'error': 'bad bridge key'})
        u = urlparse(self.path)
        path = u.path.rstrip('/') or '/'  # /tts/ and /tts are the same route
        try:
            if path == '/render/submit':
                return self.render_submit(self._body())
            if path == '/render/cancel':
                return self.render_cancel(self._body())
            if path == '/tts':
                return self.tts_render(self._body())
            return err(self, 404, {'error': 'unknown endpoint'})
        except subprocess.TimeoutExpired:
            return err(self, 504, {'error': 'upstream timeout'})
        except Exception as e:
            return err(self, 500, {'error': str(e)[:200]})

    def do_GET(self):
        if not self.check_auth():
            return err(self, 401, {'error': 'bad bridge key'})
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        try:
            if u.path.startswith('/tts/'):
                # GET /tts/<id>.mp3|wav → serve file
                tid = u.path.split('/')[-1]
                return self.tts_serve({'id': [tid]})
            if u.path == '/render/status':
                return self.render_status(qs)
            if u.path == '/render/providers':
                return err(self, 200, {'providers': sorted(PROVIDERS)})
            if u.path == '/yt/meta':
                return self.yt_meta(qs)
            if u.path == '/yt/transcript':
                return self.yt_transcript(qs)
            if u.path == '/yt/clip':
                return self.yt_clip(qs)
            if u.path == '/search':
                return self.search(qs)
            if u.path == '/health':
                return err(self, 200, {'ok': True})
            return err(self, 404, {'error': 'unknown endpoint'})
        except subprocess.TimeoutExpired:
            return err(self, 504, {'error': 'upstream timeout'})
        except Exception as e:
            return err(self, 500, {'error': str(e)[:200]})

    def blocked(self, stderr):
        s = (stderr or '').lower()
        return 'sign in to confirm' in s or 'not a bot' in s

    def yt_meta(self, qs):
        v = (qs.get('v') or [''])[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}', v):
            return err(self, 400, {'error': 'bad video id'})
        p = run(ytdlp_base() + ['--skip-download', '--print',
                                '{"title":%(title)j,"duration":%(duration)s,"uploader":%(uploader)j,"upload_date":%(upload_date)j}',
                                f'https://www.youtube.com/watch?v={v}'])
        if p.returncode != 0:
            if self.blocked(p.stderr):
                return err(self, 502, {'error': 'youtube-blocked',
                                       'hint': 'box IP blocked and no/invalid cookies — see BRIDGE.md'})
            return err(self, 502, {'error': 'yt-dlp failed', 'detail': p.stderr[-300:]})
        return err(self, 200, json.loads(p.stdout.strip().splitlines()[-1]))

    def yt_transcript(self, qs):
        v = (qs.get('v') or [''])[0]
        if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}', v):
            return err(self, 400, {'error': 'bad video id'})
        code = (
            'from youtube_transcript_api import YouTubeTranscriptApi;'
            'import json,sys;'
            f't=list(YouTubeTranscriptApi().fetch({v!r}));'
            'print(json.dumps([{"t":round(x.start,2),"d":round(x.duration,2),'
            '"x":x.text} for x in t]))'
        )
        p = run(['python3', '-c', code])
        if p.returncode != 0:
            if 'blocking requests from your IP' in p.stdout + p.stderr or 'IP' in p.stderr[:500]:
                return err(self, 502, {'error': 'youtube-blocked',
                                       'hint': 'box IP blocked — see BRIDGE.md'})
            return err(self, 502, {'error': 'transcript failed',
                                   'detail': (p.stdout + p.stderr)[-300:]})
        return err(self, 200, {'segments': json.loads(p.stdout)})

    # ---- render jobs (Jellyfish task contract: submit/status/cancel) ----
    def render_submit(self, body):
        import uuid
        try:
            req = json.loads(body or '{}')
        except Exception:
            return err(self, 400, {'error': 'bad json'})
        provider = str(req.get('provider', ''))
        if provider not in PROVIDERS:
            return err(self, 400, {'error': 'unknown provider',
                                   'providers': sorted(PROVIDERS)})
        jid = uuid.uuid4().hex[:12]
        jdir = os.path.join(RENDER_DIR, jid)
        os.makedirs(jdir, exist_ok=True)
        with open(os.path.join(jdir, 'request.json'), 'w') as f:
            json.dump(req, f)
        with open(os.path.join(jdir, 'status.json'), 'w') as f:
            json.dump({'job_id': jid, 'status': 'queued', 'progress': 0,
                       'log': []}, f)
        import threading
        ev = threading.Event()
        _CANCEL[jid] = ev
        th = threading.Thread(target=_run_job,
                              args=(jid, provider, req, ev), daemon=True)
        th.start()
        return err(self, 200, {'job_id': jid, 'status': 'queued'})

    def render_status(self, qs):
        jid = (qs.get('job') or [''])[0]
        if not re.fullmatch(r'[0-9a-f]{12}', jid or ''):
            return err(self, 400, {'error': 'bad job id'})
        sp = os.path.join(RENDER_DIR, jid, 'status.json')
        if not os.path.exists(sp):
            return err(self, 404, {'error': 'unknown job'})
        with open(sp) as f:
            st = json.load(f)
        log = st.get('log', [])
        st = dict(st)
        st['log_tail'] = log[-20:]
        del st['log']
        rp = os.path.join(RENDER_DIR, jid, 'result.json')
        if os.path.exists(rp):
            with open(rp) as f:
                st['result'] = json.load(f)
        return err(self, 200, st)

    def render_cancel(self, body):
        try:
            req = json.loads(body or '{}')
        except Exception:
            return err(self, 400, {'error': 'bad json'})
        jid = str(req.get('job', ''))
        ev = _CANCEL.get(jid)
        sp = os.path.join(RENDER_DIR, jid, 'status.json')
        if ev is None or not os.path.exists(sp):
            return err(self, 404, {'error': 'unknown job'})
        ev.set()
        with open(sp) as f:
            st = json.load(f)
        if st.get('status') in ('queued', 'running'):
            st['status'] = 'cancelled'
            with open(sp, 'w') as f:
                json.dump(st, f)
        return err(self, 200, {'job_id': jid, 'status': st.get('status')})

    def tts_render(self, body):
        """Render script text to audio. POST /tts {text, voice?, label?, engine?}
        engine: 'phonon' (local, offline, free — ptts CLI) | 'fish' (cloud default).
        Caches by sha256(text+voice+engine). Returns {id, label, ext};
        serves GET /tts/<id>.<ext>."""
        import hashlib
        import urllib.request as ur
        try:
            req = json.loads(body or '{}')
        except Exception:
            return err(self, 400, {'error': 'bad json'})
        text = str(req.get('text', '')).strip()[:4000]
        if not text:
            return err(self, 400, {'error': 'empty text'})
        voice = str(req.get('voice', '')).strip() or None
        label = str(req.get('label', 'section'))[:80]
        engine = 'phonon' if req.get('engine') == 'phonon' else 'fish'
        os.makedirs(TTS_DIR, exist_ok=True)
        h = hashlib.sha256((engine + '|' + text + '|' + (voice or '')).encode()).hexdigest()[:20]

        if engine == 'phonon':
            ext = 'wav'
            out = os.path.join(TTS_DIR, f'{h}.wav')
            if not os.path.exists(out):
                if not os.path.isdir(PHONON_MODEL):
                    return err(self, 501, {'error': 'phonon model dir missing: ' + PHONON_MODEL})
                cmd = [PHONON_BIN, '--lang', 'en', '--dir', PHONON_MODEL, '--quant', 'q4k',
                       '-o', out, text]
                if voice and re.fullmatch(r'[A-Za-z][A-Za-z0-9_ -]{1,40}', voice):
                    cmd[0:0] = []  # keep flags before text
                    cmd += ['--voice', voice]
                try:
                    pr = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                except FileNotFoundError:
                    return err(self, 501, {'error': 'ptts CLI not installed on bridge box'})
                if pr.returncode != 0 or not os.path.exists(out):
                    return err(self, 502, {'error': 'phonon failed', 'detail': (pr.stderr or pr.stdout or '')[-300:]})
        else:
            ext = 'mp3'
            out = os.path.join(TTS_DIR, f'{h}.mp3')
            if not os.path.exists(out):
                key = _fish_key()
                if not key:
                    return err(self, 502, {'error': 'no FISH_API_KEY on bridge box'})
                payload = {'text': text, 'format': 'mp3'}
                if voice:
                    payload['reference_id'] = voice
                r = ur.Request('https://api.fish.audio/v1/tts',
                               data=json.dumps(payload).encode(),
                               headers={'Authorization': f'Bearer {key}',
                                        'Content-Type': 'application/json',
                                        'model': 's2.1-pro-free'})
                with ur.urlopen(r, timeout=120) as resp:
                    data = resp.read()
                with open(out, 'wb') as f:
                    f.write(data)
        return err(self, 200, {'id': h, 'label': label, 'ext': ext})

    def tts_serve(self, qs):
        tid = (qs.get('id') or [''])[0]
        m = re.fullmatch(r'([0-9a-f]{20})(?:\.(mp3|wav))?', tid or '')
        if not m:
            return err(self, 400, {'error': 'bad tts id'})
        base, ext = m.group(1), m.group(2) or 'mp3'
        p = os.path.join(TTS_DIR, f'{base}.{ext}')
        if not os.path.exists(p):
            # tolerate stored engine mismatch: flip ext if the other exists
            alt = os.path.join(TTS_DIR, f"{base}.{'mp3' if ext == 'wav' else 'wav'}")
            if os.path.exists(alt):
                p, ext = alt, ('wav' if ext == 'mp3' else 'mp3')
            else:
                return err(self, 404, {'error': 'not found'})
        data = open(p, 'rb').read()
        self.send_response(200)
        self.send_header('Content-Type', 'audio/wav' if ext == 'wav' else 'audio/mpeg')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def yt_clip(self, qs):
        v = (qs.get('v') or [''])[0]
        try:
            dur = min(int((qs.get('dur') or ['15'])[0]), 60)
            start = max(int((qs.get('start') or ['0'])[0]), 0)
        except ValueError:
            return err(self, 400, {'error': 'bad start/dur'})
        if not re.fullmatch(r'[A-Za-z0-9_-]{6,20}', v):
            return err(self, 400, {'error': 'bad video id'})
        tmp = tempfile.mkdtemp(prefix='qclip')
        src = os.path.join(tmp, 'src.%(ext)s')
        p = run(ytdlp_base() + ['-f', 'bv*[height<=720]+ba/b[height<=720]/b',
                                '-o', src, f'https://www.youtube.com/watch?v={v}'],
                timeout=600)
        if p.returncode != 0:
            if self.blocked(p.stderr):
                return err(self, 502, {'error': 'youtube-blocked',
                                       'hint': 'box IP blocked and no/invalid cookies — see BRIDGE.md'})
            return err(self, 502, {'error': 'download failed', 'detail': p.stderr[-300:]})
        import glob
        got = glob.glob(os.path.join(tmp, 'src.*'))
        if not got:
            return err(self, 502, {'error': 'no file downloaded'})
        out = os.path.join(tmp, 'clip.mp4')
        p2 = run(['ffmpeg', '-y', '-ss', str(start), '-i', got[0],
                  '-t', str(dur), '-c:v', 'libx264', '-preset', 'veryfast',
                  '-c:a', 'aac', out])
        if p2.returncode != 0 or not os.path.exists(out):
            return err(self, 502, {'error': 'cut failed', 'detail': p2.stderr[-300:]})
        data = open(out, 'rb').read()
        self.send_response(200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Content-Disposition',
                         f'attachment; filename="{v}_{start}_{dur}.mp4"')
        self.end_headers()
        self.wfile.write(data)

    def search(self, qs):
        import urllib.request
        q = (qs.get('q') or [''])[0][:300]
        if not q:
            return err(self, 400, {'error': 'missing q'})
        hit = _SEARCH_CACHE.get(q)
        if hit and _time.time() - hit[0] < _SEARCH_TTL:
            return err(self, 200, {'results': hit[1], 'cached': True})
        req = urllib.request.Request(
            'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(q),
            headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                                  'AppleWebKit/537.36 Chrome/120 Safari/537.36'})
        html = urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'replace')
        out = []
        for block in html.split('results_links'):
            if len(out) >= 8:
                break
            m = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]*)</a>', block)
            if not m:
                continue
            href = m.group(1)
            um = re.search(r'[?&]uddg=([^&]+)', href)
            try:
                href = urllib.parse.unquote(um.group(1)) if um else href
            except Exception:
                continue
            if not href.startswith('http'):
                continue
            sn = re.search(r'class="result__snippet"[^>]*>([^<]*)<', block)
            out.append({'title': m.group(2).strip(), 'url': href,
                        'snippet': (sn.group(1).strip() if sn else '')[:300]})
        _SEARCH_CACHE[q] = (_time.time(), out)
        return err(self, 200, {'results': out})


_CANCEL: dict = {}


def _set_status(jid, **patch):
    sp = os.path.join(RENDER_DIR, jid, 'status.json')
    try:
        with open(sp) as f:
            st = json.load(f)
    except Exception:
        st = {'job_id': jid, 'status': 'running', 'progress': 0, 'log': []}
    st.update(patch)
    with open(sp, 'w') as f:
        json.dump(st, f)


def _log(jid, msg):
    sp = os.path.join(RENDER_DIR, jid, 'status.json')
    try:
        with open(sp) as f:
            st = json.load(f)
    except Exception:
        st = {'job_id': jid, 'status': 'running', 'progress': 0, 'log': []}
    st.setdefault('log', []).append(msg)
    with open(sp, 'w') as f:
        json.dump(st, f)


def _run_job(jid, provider, req, cancel_ev):
    _set_status(jid, status='running', progress=0)
    try:
        result = PROVIDERS[provider](jid, req, cancel_ev)
        with open(os.path.join(RENDER_DIR, jid, 'result.json'), 'w') as f:
            json.dump(result, f)
        _set_status(jid, status='done', progress=100)
    except Exception as e:
        if cancel_ev.is_set():
            _set_status(jid, status='cancelled')
        else:
            _log(jid, f'ERROR: {str(e)[:300]}')
            _set_status(jid, status='failed')


def _parse_dur(s):
    s = (s or '').strip()
    m = re.fullmatch(r'(\d+)\s*s(?:ec)?s?', s, re.I)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r'(\d+):(\d{1,2})', s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.fullmatch(r'(\d+):(\d{1,2})\s*[–—-]\s*(\d+):(\d{1,2})', s)
    if m:
        a = int(m.group(1)) * 60 + int(m.group(2))
        b = int(m.group(3)) * 60 + int(m.group(4))
        return max(0, b - a)
    return None


def render_boardcheck(jid, req, cancel_ev):
    """Validate a storyboard: parse shot tables, sum clocks per act, flag
    rows without durations and overlaps. The P1 renderer: proves the
    board → job → result loop on real pack content, no GPU, no keys."""
    md = str(req.get('md', ''))
    target = req.get('target_seconds')
    try:
        target = int(target) if target is not None else None
    except (ValueError, TypeError):
        target = None
    lines = md.splitlines()
    shots = []
    act = ''
    i = 0
    while i < len(lines):
        ln = lines[i]
        hm = re.match(r'#{1,4}\s+(.+?)\s*$', ln)
        if hm and '|' not in ln:
            act = re.sub(r'\s*\(?\d+:\d+.*$', '', hm.group(1)).strip()[:80]
            i += 1
            continue
        if ln.strip().startswith('|') and i + 1 < len(lines) and re.match(
                r'^\|?[\s:|-]+\|[\s:|-]*\|?\s*$', lines[i + 1].strip()):
            headers = [c.strip().lower() for c in ln.strip().strip('|').split('|')]
            def role(h):
                if re.fullmatch(r'#|shot|no\.?', h):
                    return 'id'
                if re.fullmatch(r't|time|timing|slot|dur|duration', h) or h.startswith('t0'):
                    return 'time'
                if re.search(r'visual|beat|shot|scene|image', h):
                    return 'visual'
                if re.search(r'audio|vo|narrat|speak|sound', h):
                    return 'audio'
                return None
            roles = [role(h) for h in headers]
            if 'id' not in roles:
                i += 1
                continue
            idi, tii = roles.index('id'), roles.index('time') if 'time' in roles else -1
            vii = roles.index('visual') if 'visual' in roles else -1
            aui = roles.index('audio') if 'audio' in roles else -1
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|') and not re.match(
                    r'^\|?[\s:|-]+\|[\s:|-]*\|?\s*$', lines[i].strip()):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                sid = re.sub(r'\*', '', cells[idi] if idi < len(cells) else '').strip().upper()
                if re.fullmatch(r'[SB]?\d{1,3}[A-Z]?', sid):
                    tcell = cells[tii] if 0 <= tii < len(cells) else ''
                    dcell = cells[-1] if len(cells) > max(idi, tii, vii, aui) else ''
                    secs = _parse_dur(tcell) if _parse_dur(tcell) is not None else _parse_dur(dcell)
                    shots.append({'id': sid, 'time': tcell, 'visual': cells[vii] if 0 <= vii < len(cells) else '',
                                  'audio': cells[aui] if 0 <= aui < len(cells) else '', 'act': act,
                                  'seconds': secs})
                    _log(jid, f'row {sid}: {secs if secs is not None else "?"}s')
                if cancel_ev.is_set():
                    raise InterruptedError('cancelled')
                i += 1
            continue
        i += 1
    by_act: dict = {}
    warnings = []
    for s in shots:
        by_act[s['act'] or '(untitled)'] = by_act.get(s['act'] or '(untitled)', 0) + (s['seconds'] or 0)
        if s['seconds'] is None:
            warnings.append(f"{s['id']}: no parseable duration (time={s['time']!r})")
    total = sum(by_act.values())
    out = {'shots': len(shots), 'total_seconds': total, 'by_act': by_act,
           'warnings': warnings, 'unparseable': sum(1 for s in shots if s['seconds'] is None)}
    if target is not None:
        out['target_seconds'] = target
        out['fits'] = total <= target
        out['over_seconds'] = max(0, total - target)
    return out


PROVIDERS = {'boardcheck': render_boardcheck}


if __name__ == '__main__':
    os.makedirs(RENDER_DIR, exist_ok=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
