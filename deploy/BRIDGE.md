# quill-bridge — box-side helper (TTS + yt-dlp + transcripts + clips + render jobs)

Runs on this box. quill's worker proxies `/api/yt/*`, `/api/render/*` and
`/api/tts/*` here (see `BRIDGE_URL` worker secret).

## Tunnels — named, permanent (2026-10-20)
- `named-tunnel.service` runs the account tunnel `a8ed074a` via
  `/root/.cloudflared/studio-dash.yml` — ingress for
  `quill-bridge.agi.xn--q9jyb4c` → `http://127.0.0.1:18787`.
  BRIDGE_URL = `https://quill-bridge.agi.xn--q9jyb4c`.
- Quick tunnels (trycloudflare) NEVER routed from this box (edge 404 after
  registration) — `quill-tunnel.service` kept disabled.
- The token tunnel API is closed to our CF token (7003 on /tunnels &
  /cfd_tunnel) — editing studio-dash.yml ingress is the working path.
- If the hostname 404s: `systemctl restart named-tunnel.service` and check
  `/tmp/named-tunnel.log` for 4 registered connections.

## TTS engines (POST /tts {text, voice?, label?, engine?} → {id, ext})
- **phonon** (default in the app): local, offline, free — `~/.cargo/bin/ptts`
  with `/root/phonon/model-31m-en` (q4k, 54MB). ~5s cold per call, caches
  by sha256(engine|text|voice). Voice: phonon voice names (see
  `ptts --model ... --list-voices`), NOT fish hex IDs.
- **fish** (cloud): FISH_API_KEY from /root/.fish-env or freaktown/.env,
  reference_id = fish clone hex. s2.1-pro-free.
- Serve: GET /tts/<id>.mp3|wav → cached file, Content-Type by ext.


## Endpoints (all need `X-Bridge-Key` unless BRIDGE_KEY unset)
- `GET /health` → `{"ok": true}`
- `GET /yt/meta?v=ID` → title/duration/uploader (yt-dlp, no download)
- `GET /yt/transcript?v=ID` → timed segments (youtube-transcript-api)
- `GET /yt/clip?v=ID&start=SS&dur=N` (N≤60) → mp4 slice (download + ffmpeg)
- `GET /search?q=` → DuckDuckGo results (box parity for worker /api/search)
- `POST /render/submit {provider, ...params}` → `{job_id, status: queued}`
- `GET /render/status?job=ID` → `{status, progress, log_tail, result?}`
- `POST /render/cancel {job}` → cancels queued/running job
- `GET /render/providers` → `["boardcheck", ...]`

## Render providers (BlueFish adapter pattern)
Add a renderer by implementing one function — no other code changes:

```python
def render_mything(job_id: str, req: dict, cancel_ev: threading.Event) -> dict:
    """req = submit params. Check cancel_ev.is_set() in loops; raise
    InterruptedError('cancelled') to stop. Return JSON-serializable result
    (saved as result.json). Use _log(job_id, msg) for progress lines."""
    ...
PROVIDERS = {'boardcheck': render_boardcheck, 'mything': render_mything, ...}
```

Shipped: `boardcheck` (validates storyboard clocks — deterministic, no keys).
Next: `hyperframes` (SVG scenes → frames via the gcomedy stack),
`pil-scenes` (PIL storyboard stills). Both run box-locally; results land in
`/root/.quill-render/jobs/<id>/` (status.json, log, result.json, artifacts).

## YouTube cookies (the one manual step)
This box's datacenter IP is hard-blocked by YouTube ("Sign in to confirm
you're not a bot", all clients). Until ONE of these happens, yt endpoints
answer 502 `youtube-blocked` (honest, never fake data):
1. **Export cookies** (owner, 2 min): in a logged-in desktop browser,
   extension "Get cookies.txt LOCALLY" → export youtube.com → save as
   `/root/.yt-cookies.txt` (600). Bridge picks it up automatically.
2. **Move the bridge**: run `bridge.py` on an unblocked box (home machine,
   residential IP), point a tunnel at it, update `BRIDGE_URL` worker
   secret. No app rebuild needed — the URL is config, not code.

## YouTube Data API key (/root/.youtube-env)
Present but quota-guarded (search = 100 units/call; file says DO NOT SPEND
without owner approval). NOT wired: metadata needs no key beyond yt-dlp,
transcripts can't use API keys (OAuth-only), downloads never via API.
