#!/usr/bin/env python3
"""quill MCP server — exposes the quill copilot loop as MCP tools.

Mirrors the in-app contracts exactly:
- sweep prompt == src/services/ai.ts buildSweepPrompt
- system prompt == DEFAULT_AI_SETTINGS customPrompts['manuscript-ai'] (compiler law)
- verify budget == verifyClaimAgainstSources (20000 chars, per-source share)
- boardcheck == bridge /render submit+poll (Jelly admitted... Jellyfish task contract)

Env:
  QUILL_PACKS_DIR  (default /root/manuscriptAI/public/packs)
  OPENCODE_GO_API_KEY (fallback: /root/.hermes/profiles/builder/.env)
  OPENCODE_GO_MODEL   (default longcat-2.5-preview-free — matches app default)
  BRIDGE_URL (default http://127.0.0.1:18787), BRIDGE_KEY (default /root/.bridge-key)

Run: python3 quill_mcp.py   (stdio)
"""
import json
import os
import re
import sys
import urllib.request
import uuid

from mcp.server.fastmcp import FastMCP

PACKS_DIR = os.environ.get('QUILL_PACKS_DIR', '/root/manuscriptAI/public/packs')
BRIDGE_URL = os.environ.get('BRIDGE_URL', 'http://127.0.0.1:18787').rstrip('/')
GO_URL = 'https://opencode.ai/zen/go/v1/chat/completions'
GO_MODEL = os.environ.get('OPENCODE_GO_MODEL', 'longcat-2.5-preview-free')


def _go_key() -> str:
    # File first (fresh — shell env may hold an expired key), env fallback.
    try:
        with open('/root/.hermes/profiles/builder/.env') as f:
            for line in f:
                if line.startswith('OPENCODE_GO_API_KEY='):
                    k = line.strip().split('=', 1)[1]
                    if k.startswith('oc_sk_') or k.startswith('sk-'):
                        return k
    except OSError:
        pass
    k = os.environ.get('OPENCODE_GO_API_KEY') or os.environ.get('OC_GO_API_KEY', '')
    if k:
        return k
    return ''


def _bridge_key() -> str:
    if os.environ.get('BRIDGE_KEY'):
        return os.environ['BRIDGE_KEY']
    try:
        return open('/root/.bridge-key').read().strip()
    except OSError:
        return ''


# --- exact mirror of DEFAULT_AI_SETTINGS customPrompts['manuscript-ai'] ---
SYSTEM_COMPILER = """You are the owner's script COMPILER for gochema essay-films (Buddhist reincarnation series + 13 tradition films). Compiler law — binding on every reply:
1. You COMPILE, never author. The owner's words ([OWNER VERBATIM] / draft1) are immutable — never rephrase, smooth, or "improve" them. Suggest cuts with […] only.
2. [READ — cite] lines are verbatim from the attached sources. If the manuscript's quote differs from the source by even a word, flag it EXACTLY (manuscript wording vs source wording) and propose the verbatim fix.
3. Doctrines come from the teachers in their own words (quotes + clips). The narrator bridges, never paraphrases a position a teacher could state. If a bridge paragraph states doctrine, rewrite it as quote-setup + [READ], or flag it DRAFT.
4. Never invent citations, numbers, Pali/Sanskrit terms, dates, or clip windows. If a manuscript claim has no attached-source backing, say SILENT and name which source should carry it.
5. New narration you draft must be in the owner's register (short, dry, direct) and marked [DRAFT — owner to voice] so it never mixes with locked text.
Cite evidence as file + quote ID (e.g. WEAVE M1, resources/05, quotes/sn12.015.than.txt)."""


def build_sweep_prompt(section_title, section_text, focus=''):
    head = f'Section "{section_title}"' if section_title else 'Section'
    extra = f'\nSweep focus (owner\'s words): {focus}' if focus else ''
    return f"""SWEEP the manuscript section below. Attached sources are the ONLY evidence allowed — a claim with no attached-source backing is SILENT, never assumed.

Return exactly these four markdown sections, terse. No other prose.

## Verdicts
One line per checkable claim: SUPPORTED | SILENT | CONTRADICTED + the source + ID (e.g. WEAVE K12, M1, SN 12.67). No explanation beyond the verdict line.

## READ checks
For every quoted passage: manuscript wording vs source wording side by side. Flag ANY difference, however small, and propose the verbatim fix as an [originalText → suggestedText] pair. If no quotes, write "none".

## Implications
3–5 bullets, each exactly: verdict → crux (one sentence: why it matters) → evidence (source ID) → forward-link (what this unlocks next) → next question (one open question this raises). This chain is the point of the sweep.

## Drafts
At most 3 bridge lines, each marked [DRAFT — owner to voice], only where the section has gaps. Never rewrite, smooth, or "improve" the owner's sentences.{extra}

{head}:
\"\"\"
{section_text.strip()[:12000]}
\"\"\"
"""


def _go_chat(system, user, max_tokens=4096, temperature=0.3):
    key = _go_key()
    if not key:
        raise RuntimeError('no Go API key (env OPENCODE_GO_API_KEY or hermes builder .env)')
    body = json.dumps({
        'model': GO_MODEL,
        'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
        'temperature': temperature,
        'max_tokens': max_tokens,
        'enable_thinking': False, 'think': False,
        'chat_template_kwargs': {'enable_thinking': False},
    }).encode()
    req = urllib.request.Request(
        GO_URL, data=body,
        headers={'Content-Type': 'application/json',
                 'Authorization': f'Bearer {key}',
                 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
                 'x-opencode-session': str(uuid.uuid4())})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    try:
        return d['choices'][0]['message'].get('content') or ''
    except (KeyError, IndexError):
        return json.dumps(d)[:2000]


def _manifest():
    with open(os.path.join(PACKS_DIR, 'packs.json')) as f:
        return json.load(f)


def _read_source(slug, name):
    p = os.path.normpath(os.path.join(PACKS_DIR, slug, 'sources', name))
    base = os.path.normpath(os.path.join(PACKS_DIR, slug, 'sources'))
    if not p.startswith(base + os.sep):
        raise ValueError('bad source path')
    with open(p, encoding='utf-8', errors='replace') as f:
        return f.read()


def _read_manuscript(slug, name):
    p = os.path.normpath(os.path.join(PACKS_DIR, slug, 'manuscripts', name))
    base = os.path.normpath(os.path.join(PACKS_DIR, slug, 'manuscripts'))
    if not p.startswith(base + os.sep):
        raise ValueError('bad manuscript path')
    with open(p, encoding='utf-8', errors='replace') as f:
        return f.read()


def _bridge(path, body=None, timeout=60):
    url = BRIDGE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {'Content-Type': 'application/json'}
    bk = _bridge_key()
    if bk:
        headers['X-Bridge-Key'] = bk
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method='POST' if data else 'GET')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode('utf-8', 'replace')


mcp = FastMCP('quill')


@mcp.tool()
def packs_list() -> str:
    """List available video-idea packs (slug, title, manuscript + source counts)."""
    ps = _manifest().get('packs', [])
    return '\n'.join(
        f"- {p['slug']}: {p.get('title','')} "
        f"[{len(p.get('manuscripts',[]))} md, {len(p.get('sources',[]))} src]"
        for p in ps)


@mcp.tool()
def pack_get(slug: str) -> str:
    """Get a pack: blurb, manuscript texts (full), and source file list."""
    m = _manifest()
    pack = next((p for p in m.get('packs', []) if p['slug'] == slug), None)
    if not pack:
        return f'unknown pack "{slug}"'
    out = [f"# {pack.get('title', slug)}", '', (pack.get('blurb') or '').strip(), '']
    for doc in pack.get('manuscripts', []):
        try:
            out += [f"## manuscript: {doc['file']}", _read_manuscript(slug, doc['file']), '']
        except OSError as e:
            out.append(f'(missing {doc["file"]}: {e})')
    out.append('## sources (use pack_source for full text):')
    for s in pack.get('sources', []):
        fp = os.path.join(PACKS_DIR, slug, 'sources', s)
        try:
            out.append(f'- {s} ({os.path.getsize(fp)} bytes)')
        except OSError:
            out.append(f'- {s} (missing)')
    return '\n'.join(out)


@mcp.tool()
def pack_source(slug: str, name: str) -> str:
    """Full text of one pack source file (e.g. WEAVE.md, quotes-*.txt)."""
    try:
        return _read_source(slug, name)
    except (OSError, ValueError) as e:
        return f'unreadable: {e}'


@mcp.tool()
def sweep(section_title: str, section_text: str, pack: str, sources: list[str], focus: str = "") -> str:
    """Sweep a manuscript section: verdicts + READ checks + implications + drafts.
    sources: attached pack source filenames (the ONLY evidence allowed)."""
    ctx = []
    for s in sources:
        try:
            ctx.append(f'=== {s} ===\n{_read_source(pack, s)}')
        except (OSError, ValueError) as e:
            ctx.append(f'=== {s} === (unreadable: {e})')
    prompt = build_sweep_prompt(section_title, section_text, focus)
    prompt += '\nAttached sources:\n"""\n' + '\n\n'.join(ctx)[:50000] + '\n"""\n'
    return _go_chat(SYSTEM_COMPILER, prompt)


@mcp.tool()
def verify_claim(claim: str, pack: str, sources: list[str]) -> str:
    """Check ONE claim against attached pack sources: SUPPORTED | SILENT | CONTRADICTED, with quote."""
    ctx = []
    for s in sources:
        try:
            ctx.append(_read_source(pack, s))
        except (OSError, ValueError):
            pass
    max_chars, per = 20000, max(1, len(ctx) or 1)
    joined = '\n\n'.join(t[: max_chars // per] for t in ctx)[:max_chars]
    prompt = ('Claim from manuscript:\n"' + claim + '"\n\nReference sources:\n"""\n'
              + joined + '\n"""\n\nDoes the evidence SUPPORT, CONTRADICT, or stay SILENT? '
                'State the verdict in the first sentence, quote the most relevant passage, '
                'note caveats. Under 250 words.')
    sys = ('You are a scientific fact-checker. Assess whether uploaded reference sources support, '
           'contradict, or fail to address a specific manuscript claim. Be precise, quote relevant '
           'evidence, and keep your response under 250 words.')
    return _go_chat(sys, prompt, max_tokens=1024)


@mcp.tool()
def lookup_quote(query: str, pack: str) -> str:
    """Find a WEAVE/quote ID verbatim in a pack's sources. No LLM — deterministic grep with context."""
    q = query.strip()
    if not q:
        return 'Empty quote ID.'
    m = _manifest()
    packd = next((p for p in m.get('packs', []) if p['slug'] == pack), None)
    if not packd:
        return f'unknown pack "{pack}"'
    needles = [q] + ([q[5:]] if q.upper().startswith('WEAVE ') else [])
    hits = []
    for s in packd.get('sources', []):
        try:
            t = _read_source(pack, s)
        except (OSError, ValueError):
            continue
        low = t.lower()
        for n in dict.fromkeys(needles):
            i = low.find(n.lower())
            if i >= 0:
                a, b = max(0, i - 400), min(len(t), i + len(n) + 400)
                hits.append(f'=== {s} ===\n…' + re.sub(r'\s+', ' ', t[a:b]).strip() + '…')
                if len(hits) >= 5:
                    break
        if len(hits) >= 5:
            break
    return '\n\n'.join(hits) if hits else f'Not found: "{q}" in pack "{pack}".'


@mcp.tool()
def boardcheck(pack: str, target_seconds: int = 1800) -> str:
    """Validate a pack's storyboard clock deterministically: shots, per-act totals, untimed rows. No LLM."""
    m = _manifest()
    packd = next((p for p in m.get('packs', []) if p['slug'] == pack), None)
    if not packd:
        return f'unknown pack "{pack}"'
    mans = [d['file'] for d in packd.get('manuscripts', [])]
    doc = next((x for x in ['STORYBOARD.md', 'MOVIE.md'] if x in mans), None)
    if not doc:
        return f'pack "{pack}" has no STORYBOARD.md or MOVIE.md'
    md = _read_manuscript(pack, doc)
    import time
    st, body = _bridge('/render/submit', {'provider': 'boardcheck', 'pack': pack,
                                          'md': md, 'target_seconds': target_seconds})
    if st != 200:
        return f'submit failed HTTP {st}: {body[:200]}'
    job = json.loads(body).get('job_id', '')
    for _ in range(20):
        time.sleep(3)
        st2, b2 = _bridge(f'/render/status?job={job}')
        if st2 != 200:
            return f'status HTTP {st2}'
        d = json.loads(b2)
        if d.get('status') == 'done' and 'result' in d:
            r = d['result']
            def mmss(s):
                return f'{s // 60}:{s % 60:02d}'
            lines = [f"Boardcheck {pack}/{doc}: {r['shots']} shots, {mmss(r['total_seconds'])} total."]
            for act, secs in (r.get('by_act') or {}).items():
                lines.append(f'- {act}: {mmss(secs)}')
            if isinstance(r.get('fits'), bool):
                lines.append('Fits the 30:00 budget.' if r['fits'] else f"OVER budget by {mmss(r.get('over_seconds', 0))}.")
            warns = r.get('warnings', [])
            if warns:
                lines.append(f'Warnings ({len(warns)} untimed rows):')
                lines.extend(warns[:12])
            return '\n'.join(lines)
        if d.get('status') in ('failed', 'cancelled'):
            return f"job {d.get('status')}"
    return f'job {job} still running'


@mcp.tool()
def canon_search(query: str, lang: str = "", limit: int = 5) -> str:
    """Semantic search across the Buddhist canon (10K+ texts, 30+ langs) via FoJin.
    lang filters: pi=Pali, sa=Sanskrit, lzh=Classical Chinese, bo=Tibetan, en=English.
    Returns passages with portable URNs (fojin:cbeta/T0251.1) for citation."""
    import urllib.parse
    args = {'query': query[:500]}
    if lang:
        args['lang'] = lang
    args['limit'] = max(1, min(20, limit))
    body = json.dumps({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                       'params': {'name': 'search_corpus', 'arguments': args}}).encode()
    req = urllib.request.Request('https://mcp.fojin.ai/mcp', data=body,
        headers={'Content-Type': 'application/json',
                 'Accept': 'application/json, text/event-stream',
                 'User-Agent': 'quill/0.1 (Mozilla/5.0)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    try:
        text = d['result']['content'][0]['text']
        inner = json.loads(text)
        out = []
        for hit in inner.get('results', [])[:limit]:
            out.append(f"URN: {hit.get('urn','?')}\n  {hit.get('title_zh','')} ({hit.get('cbeta_id','')})\n  score: {hit.get('score',0):.3f}\n  {hit.get('snippet','').strip()[:400]}")
        return '\n'.join(out) if out else 'No results found.'
    except (KeyError, IndexError, ValueError):
        return f'FoJin error: {json.dumps(d)[:600]}'


def _fojin_call(tool, arguments, rid=4, timeout=30):
    body = json.dumps({'jsonrpc': '2.0', 'id': rid, 'method': 'tools/call',
                       'params': {'name': tool, 'arguments': arguments}}).encode()
    req = urllib.request.Request('https://mcp.fojin.ai/mcp', data=body,
        headers={'Content-Type': 'application/json',
                 'Accept': 'application/json, text/event-stream',
                 'User-Agent': 'quill/0.1 (Mozilla/5.0)'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read().decode())
    try:
        return d['result']['content'][0]['text']
    except (KeyError, IndexError):
        return f'FoJin error: {json.dumps(d)[:600]}'


@mcp.tool()
def canon_read(urn: str) -> str:
    """Read a passage by canonical URN (e.g. fojin:84k/44.1).
    FoJin read_passage takes (text_id, juan_num) ints — resolve first."""
    resolved = _fojin_call('resolve_urn', {'urn': urn}, rid=41)
    tid, juan = None, None
    try:
        info = json.loads(resolved) if resolved.strip().startswith('{') else None
        if isinstance(info, dict):
            tid = info.get('text_id') or info.get('id')
            juan = info.get('juan_num') or info.get('juan') or 1
        elif isinstance(info, list) and info:
            tid = info[0].get('text_id'); juan = info[0].get('juan_num', 1)
    except (ValueError, AttributeError, TypeError):
        info = None
    if tid is None:
        # fall back: some resolvers return raw ints in text form
        m = re.search(r'"text_id"\s*:\s*(\d+)', resolved or '')
        m2 = re.search(r'"juan_num"\s*:\s*(\d+)', resolved or '')
        if m:
            tid = int(m.group(1)); juan = int(m2.group(1)) if m2 else 1
    if tid is None:
        return f'URN did not resolve: {resolved[:400]}'
    passage = _fojin_call('read_passage', {'text_id': int(tid), 'juan_num': int(juan or 1)}, rid=42)
    return f'URN: {urn} (text_id={tid}, juan={juan})\n{passage}'


@mcp.tool()
def canon_verify(quote: str) -> str:
    """Verify a quote against the Buddhist canon via FoJin. Returns matching passages + URNs.
    If the quote is found, cite the URN; if not, say SILENT."""
    return _fojin_call('verify_quote', {'quote': quote[:800]}, rid=5)


@mcp.tool()
def parallel_args(query: str, pack: str = "", focus: str = "") -> str:
    """Search the canon AND the web in parallel for one argument node.
    Returns both result sets: canon hits (FoJin URNs) + web hits (URLs).
    If pack is set, also includes the pack's existing WEAVE hits."""
    import urllib.parse
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def do_web():
        try:
            st, body = _bridge('/search?q=' + urllib.parse.quote(query[:300]))
            if st == 200:
                return f'## Web\n' + '\n\n'.join(
                    f'- {r.get("title","")}\n  {r.get("url","")}\n  {r.get("snippet","")}'
                    for r in json.loads(body).get('results', [])[:5])
        except Exception as e:
            return f'## Web (error: {e})'
        return '## Web\n(no results)'
    def do_canon():
        try:
            r = canon_search(query, limit=4)
            return f'## Canon (FoJin)\n{r}'
        except Exception as e:
            return f'## Canon (error: {e})'
    def do_pack():
        if not pack:
            return ''
        try:
            r = lookup_quote(query, pack)
            return f'## Pack WEAVE\n{r}'
        except Exception as e:
            return f'## Pack WEAVE (error: {e})'
    tasks = [do_web, do_canon, do_pack]
    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = {pool.submit(fn): fn.__name__ for fn in tasks}
        for f in as_completed(futs, timeout=45):
            try:
                results[futs[f]] = f.result()
            except Exception as e:
                results[futs[f]] = f'(timeout/error: {e})'
    out = [f'Query: {query}']
    if focus:
        out.append(f'Focus: {focus}')
    out.append('')
    out.append(results.get('do_pack', ''))
    out.append(results.get('do_canon', ''))
    out.append(results.get('do_web', ''))
    return '\n\n'.join(x for x in out if x)


# --- board / screenplay flow (deterministic, local packs only, no LLM) ---

_ACT_HEADING = re.compile(r'^##\s+(.*)$')
_TABLE_ROW = re.compile(r'^\|(.+)\|\s*$')
_QUOTE_ID = re.compile(r'\[([A-Za-z]{1,4}\d{1,3})\]')
_TIME_RANGE = re.compile(r'(\d{1,2}):(\d{2})\s*[–-]\s*(\d{1,2}):(\d{2})')
_TIME_ANY = re.compile(r'\d{1,2}:\d{2}')


def _bell_ids(cell: str):
    """'**BELL M / C / K**' → ['M','C','K']; 'BELL S (sandcastle)' → ['S']."""
    if not cell:
        return []
    txt = re.sub(r'\(.*?\)', '', cell.replace('*', ''))
    ids = []
    for part in txt.split('/'):
        part = re.sub(r'^\s*BELL\s*', '', part, flags=re.I)
        part = re.split(r'\s*[—–-]+\s*', part)[0].strip()
        m = re.match(r'([A-Za-z0-9][A-Za-z0-9\-]*)', part)
        if m and m.group(1).upper() not in ('MOTIF', 'ZONE'):
            ids.append(m.group(1))
    return ids


def _board_doc(pack: str, doc: str = ''):
    """Return (name, text) of the pack's storyboard/movie manuscript."""
    m = _manifest()
    packd = next((p for p in m.get('packs', []) if p['slug'] == pack), None)
    if not packd:
        raise ValueError(f'unknown pack "{pack}"')
    mans = [d['file'] for d in packd.get('manuscripts', [])]
    if doc:
        if doc not in mans:
            raise ValueError(f'pack "{pack}" has no manuscript {doc}')
        name = doc
    else:
        name = next((x for x in ['STORYBOARD.md', 'MOVIE.md'] if x in mans), None)
        if not name:
            raise ValueError(f'pack "{pack}" has no STORYBOARD.md or MOVIE.md')
    return name, _read_manuscript(pack, name)


def _parse_board(md: str):
    """Markdown beat-table rows → dicts (milimovideo ScriptParser pattern,
    shaped for OUR tables: | id | est t | scene | narration | bell |)."""
    act, rows = '', []
    for raw in md.splitlines():
        line = raw.rstrip()
        mh = _ACT_HEADING.match(line)
        if mh and not line.startswith('####'):
            act = mh.group(1).strip()
            continue
        mt = _TABLE_ROW.match(line.strip())
        if not mt:
            continue
        cells = [c.strip() for c in mt.group(1).split('|')]
        if not cells:
            continue
        head0 = cells[0].lstrip('* ').lower()
        if head0 in ('#', 'n', 'no', 'id', 'row') or set(head0) <= set('-: '):
            continue  # header / separator
        if all(set(c) <= set('-: ') and c for c in cells):
            continue
        rid = head0
        if not re.match(r'^[a-z]?\d+$', rid) and not re.match(r'^[a-z]+\d+$', rid):
            continue  # not a row id (skip prose tables like acts summary)
        rows.append({
            'id': cells[0],
            'act': act,
            't': cells[1] if len(cells) > 1 else '',
            'scene': cells[2] if len(cells) > 2 else '',
            'narration': cells[3] if len(cells) > 3 else '',
            'bell': cells[4] if len(cells) > 4 else '',
            'rhythm': cells[5] if len(cells) > 5 else '',
        })
    return rows


def _weave_entries(pack: str):
    """Parse pack sources for banked quote entries: id → dict(quote, raw)."""
    m = _manifest()
    packd = next((p for p in m.get('packs', []) if p['slug'] == pack), None)
    if not packd:
        raise ValueError(f'unknown pack "{pack}"')
    out = {}
    for s in packd.get('sources', []):
        try:
            t = _read_source(pack, s)
        except (OSError, ValueError):
            continue
        # entry lines: **[F7] VOICE, S5** — "verbatim…" — cite — STOP …
        # (entries wrap across lines: join continuations, keep breaks before entries)
        joined = re.sub(r'\n(?!\s*\*\*\[)', ' ', t)
        for mm in re.finditer(
                r'\*\*\[([A-Za-z]+\d+)\]\s*([^*]*)\*\*(.*?)(?=\*\*\[|\Z)',
                joined, re.S):
            eid = mm.group(1)
            if eid in out:
                continue
            rest = ' '.join(mm.group(3).split())
            qm = re.search(r'"([^"]{20,})"', rest)
            quote = ' '.join(qm.group(1).split()) if qm else ''
            # cite = text after the quote, before STOP; keep short
            cite = ''
            if qm:
                tail = rest[qm.end():]
                cite = re.split(r'\s+STOP\b', tail)[0].strip(' —-')
            out[eid] = {'id': eid, 'head': mm.group(2).strip(' —'),
                        'quote': quote, 'cite': cite.strip(' —'),
                        'source': s, 'raw': rest[:400]}
    return out


def _row_timing(t: str):
    """'0:00–0:25' → (0,25); 'tbd'/'est' free text → None; bad clock → 'bad'."""
    if not t or not _TIME_ANY.search(t):
        return None
    m = _TIME_RANGE.search(t)
    if m:
        a = int(m.group(1)) * 60 + int(m.group(2))
        b = int(m.group(3)) * 60 + int(m.group(4))
        return (a, b)
    return 'bad'


@mcp.tool()
def board_parse(pack: str, doc: str = "") -> str:
    """Parse a pack's STORYBOARD.md (or MOVIE.md) beat tables into shot rows:
    id · act · est time · scene · narration refs · bell. Deterministic, no LLM.
    The row model every other board tool and the render pass work on."""
    try:
        name, md = _board_doc(pack, doc)
    except (ValueError, OSError) as e:
        return str(e)
    rows = _parse_board(md)
    if not rows:
        return f'no beat rows parsed from {pack}/{name}'
    out = [f'{pack}/{name}: {len(rows)} rows']
    for r in rows:
        bell = f' · {r["bell"]}' if r['bell'] and r['bell'] not in ('—', '-') else ''
        rhythm = f' · R:{r["rhythm"]}' if r.get('rhythm') and r['rhythm'] not in ('—', '-') else ''
        out.append(f'  {r["id"]:>4} [{r["act"][:28]:<28}] {r["t"]:<14} {r["scene"][:60]}{bell}{rhythm}')
        if r['narration'] and r['narration'] not in ('—', '-'):
            out.append(f'        NAR: {r["narration"][:100]}')
    return '\n'.join(out)


@mcp.tool()
def board_validate(pack: str, doc: str = "") -> str:
    """Validate the pack's storyboard structurally (deterministic, no LLM):
    quote IDs exist in WEAVE · unique row IDs · bell inventory · timing
    format/order · counts of timed/untimed/draft/silent rows.
    Errors block; warnings are advisory (untimed rows are legal until the
    timing pass)."""
    try:
        name, md = _board_doc(pack, doc)
        weave = _weave_entries(pack)
    except (ValueError, OSError) as e:
        return str(e)
    rows = _parse_board(md)
    if not rows:
        return f'FAIL {pack}/{name}: no beat rows parsed'
    errors, warns = [], []
    # unique ids
    seen = set()
    for r in rows:
        if r['id'] in seen:
            errors.append(f'duplicate row id {r["id"]}')
        seen.add(r['id'])
    # narration quote refs exist in the bank
    used_ids = set()
    for r in rows:
        for qid in _QUOTE_ID.findall(r['narration'] or ''):
            used_ids.add(qid)
            if qid not in weave:
                errors.append(f'{r["id"]}: narration cites [{qid}] not in WEAVE')
    # bells: inventory + zone-walk rows should carry one
    bells = {}
    for r in rows:
        for bid in _bell_ids(r['bell'] or ''):
            bells.setdefault(bid, []).append(r['id'])
        if re.match(r'^Z\d', r['id']) and not (r['bell'] or '').strip(' —*'):
            warns.append(f'{r["id"]}: zone row has no bell')
    # timings
    timed = untimed = draft = silent = 0
    prev_end, prev_act = None, None
    for r in rows:
        nar = (r['narration'] or '').strip()
        if nar in ('—', '-', ''):
            silent += 1
        if '[DRAFT' in nar.upper():
            draft += 1
        tm = _row_timing(r['t'])
        if tm is None:
            untimed += 1
        elif tm == 'bad':
            warns.append(f'{r["id"]}: unparseable time "{r["t"]}"')
        else:
            timed += 1
            if tm[1] <= tm[0]:
                warns.append(f'{r["id"]}: end <= start ({r["t"]})')
            if r['act'] == prev_act and prev_end is not None and tm[0] < prev_end:
                warns.append(f'{r["id"]}: starts before previous row ends')
            prev_end, prev_act = tm[1], r['act']
        if r['act'] != prev_act:
            prev_end = None
            prev_act = r['act']
    status = 'FAIL' if errors else 'PASS'
    out = [f'{status} {pack}/{name}: {len(rows)} rows · '
           f'{timed} timed / {untimed} untimed · {silent} silent · {draft} [DRAFT]']
    out.append(f'quote refs used: {len(used_ids)} '
               f'({", ".join(sorted(used_ids)) or "none"})')
    out.append('bells: ' + (', '.join(f'{k}→{"/".join(v)}' for k, v in sorted(bells.items()))
                            or 'none yet'))
    if errors:
        out.append(f'errors ({len(errors)}):')
        out += [f'  ✗ {e}' for e in errors]
    if warns:
        out.append(f'warnings ({len(warns)}):')
        out += [f'  ! {w}' for w in warns[:15]]
    return '\n'.join(out)


@mcp.tool()
def quote_for_row(pack: str, row_id: str = "", keywords: str = "") -> str:
    """Pick banked quotes for a storyboard row (the fill-the-narration loop).
    Give row_id (its scene text seeds the search) and/or keywords. Returns
    the row's assigned [IDs] first, then the best-matching WEAVE entries —
    all verbatim from the bank, nothing invented (compiler law)."""
    try:
        weave = _weave_entries(pack)
        name, md = _board_doc(pack)
    except (ValueError, OSError) as e:
        return str(e)
    rows = _parse_board(md)
    row = next((r for r in rows if r['id'] == row_id), None) if row_id else None
    stop = {'the', 'and', 'with', 'that', 'this', 'from', 'into', 'over',
            'then', 'when', 'shot', 'scene', 'still', 'row', 'bell', 'motif'}
    if keywords.strip():
        seed = keywords
    elif row:
        seed = row['scene'] + ' ' + row['narration']
    else:
        return f'give row_id or keywords (bank: {len(weave)} entries)'
    toks = {w for w in re.findall(r'[a-zA-Z]{4,}', seed.lower()) if w not in stop}
    scored = []
    for eid, e in weave.items():
        hay = (e['quote'] + ' ' + e['head'] + ' ' + e['cite']).lower()
        score = sum(1 for t in toks if t in hay)
        if score:
            scored.append((score, eid, e))
    scored.sort(key=lambda x: (-x[0], x[1]))
    out = []
    if row:
        out.append(f'row {row["id"]} [{row["act"]}] {row["t"]}')
        out.append(f'  scene: {row["scene"]}')
        out.append(f'  narration: {row["narration"]}')
        assigned = _QUOTE_ID.findall(row['narration'] or '')
        for eid in assigned:
            e = weave.get(eid)
            if e:
                out.append(f'  ASSIGNED [{eid}] "{e["quote"][:160]}" — {e["cite"]}')
    if not scored:
        out.append(f'no banked match for {sorted(toks)} — SILENT (add a WEAVE entry, never invent).')
        return '\n'.join(out)
    out.append('best banked matches:')
    for score, eid, e in scored[:5]:
        out.append(f'  [{eid}] ×{score} "{e["quote"][:180]}" — {e["cite"]} (STOP {e["head"]})')
    return '\n'.join(out)


@mcp.tool()
def movie_outline(pack: str) -> str:
    """Screenwriting overview of a pack's MOVIE.md: thesis, structural
    laws, act table, READ list, open flags. Deterministic parse, no LLM."""
    try:
        name, md = _board_doc(pack, 'MOVIE.md')
    except (ValueError, OSError) as e:
        return str(e)
    def sect(title):
        m = re.search(rf'^##\s+{re.escape(title)}.*?$(.*?)(?=^##\s|\Z)',
                      md, re.M | re.S)
        return ' '.join(m.group(1).split()) if m else ''
    thesis = sect('Thesis').split('Ground:')[0].strip()
    laws = re.findall(r'^\d+\.\s+\*\*(.+?)\*\*\s*(.*)$', md, re.M)
    acts = re.findall(r'^\|\s*(A[\w\-]+\s+[^|]*?)\s*\|\s*([^|]*)\|\s*([^|]*)\|', md, re.M)
    reads = re.search(r'^## READs.*?$(.*?)(?=^##\s|\Z)', md, re.M | re.S)
    flags = re.search(r'^## Flags.*?$(.*?)(?=^##\s|\Z)', md, re.M | re.S)
    out = [f'{pack}/{name}', '', f'THESIS: {thesis[:500]}', '', 'LAWS:']
    for i, (t_, d_) in enumerate(laws, 1):
        out.append(f'  {i}. {t_} — {d_.lstrip(" —")[:140]}')
    if acts:
        out.append('')
        out.append('ACTS:')
        for a, c, r in acts:
            out.append(f'  {a.strip()}: {c.strip()[:90]} [{r.strip()}]')
    if reads:
        out.append('')
        out.append('READs: ' + ' '.join(reads.group(1).split())[:400])
    if flags:
        out.append('')
        out.append('FLAGS:')
        for fl in re.findall(r'^-\s+(.*)$', flags.group(1), re.M):
            out.append(f'  ! {fl[:180]}')
    return '\n'.join(out)


@mcp.tool()
def web_search(query: str) -> str:
    """Web search (blogs, forums, teachers) via the bridge. Honest errors when throttled."""
    import urllib.parse
    st, body = _bridge('/search?q=' + urllib.parse.quote(query[:300]))
    if st != 200:
        return f'search failed HTTP {st}'
    try:
        rs = json.loads(body).get('results', [])
    except ValueError:
        return 'search returned unparseable response'
    if not rs:
        return 'No results found.'
    return '\n\n'.join(f"[{i + 1}] {r.get('title')}\n{r.get('url')}\n{r.get('snippet', '')}"
                       for i, r in enumerate(rs[:8]))


if __name__ == '__main__':
    mcp.run()
