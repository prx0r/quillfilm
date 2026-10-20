# quill — the essay-film writing desk

> **quillfilm** — fork of prx0r/quill-app (the essay-film desk), cut for
> the nibbana motif movie: same writing surface + copilot, film packs
> under `public/packs/nibbana-movie/`. Upstream: README.upstream.md.

> Fork of [dzyla/manuscriptAI](https://github.com/dzyla/manuscriptAI) (MIT),
> rebuilt as the writing surface for **gochema** essay-films: packs of
> evidence + a compiler-law AI copilot + a blank sketch canvas + storyboard
> + render pipeline. Upstream docs: `README.upstream.md`.
> Vision: `VISION.md` · Architecture + adopt verdicts: `SPEC.md` ·
> Bridge ops: `deploy/BRIDGE.md` · Video queue: gochema `QUEUE.md`.

## Live

**https://quill.agi.みんな** — no login (private, keyless site).

| URL | Lands you on |
|---|---|
| `/?canvas=rebirth` | blank void + **the rebirth essay placed** as chapter objects |
| `/?canvas=new` | literal empty screen (click anywhere, write) |
| `/?canvas=<slug>` | void + that pack's essay (`karma`, `what-is-jhana`, …) |
| `/` | the manuscript editor (script, sources, chat) |

## The loop (how a film gets written)

1. **File → Video packs…** → Load a pack. Manuscript lands in the editor,
   evidence bank (WEAVE/resources/quotes) in the Cite library, storyboard
   rows in Write → Storyboard, argument graphs in Write → Arguments/Canvas.
2. **Write.** The AI sees your words + the pack's sources on every message
   *without attaching anything* (whole files, quote-safe), under the
   compiler law: verbatim quotes, SILENT when unbanked, your voice never
   rewritten. New narration it drafts is always `[DRAFT — owner to voice]`.
3. **⚡ copilot** (next to Send) or `/sweep` — verdicts · READ checks ·
   implication chains for the section under your cursor.
   Ask anything: `lookup_quote`, `web_search`, `verify_claim`,
   `board_check`, canon search (FoJin) all run as tools.
4. **🔊 Hear this section** (top bar → AI menu) — Phonon reads it aloud
   locally in seconds. Write → Script does it per chapter (`phonon · local`
   or `fish · cloud` voice engine).
5. **Canvas** (`?canvas=rebirth`) — the essay as movable objects: ⠿ drag
   handles, shift-click multi-select, drag the whole set, wheel zoom,
   shift+drag pan, Esc clears selection, pause 2.6s → evidence cards
   (`quote`/`source`/`objection`/`next`) pull in beside what you typed.
6. **Mark shots done** (Write → Storyboard) — the journey log accumulates.
7. Render: bridge `/api/tts` (Phonon local / Fish cloud) today; the
   hyperframes camera-flight over the canvas coordinates is next (P2).

## Packs

```
public/packs/<slug>/
  manuscripts/  ESSAY · STORYBOARD · MOVIE · draft1 · STRUCTURE · PUSHBACK …
  sources/      WEAVE.md · TAKES.md · resources-*.md · quotes-*.txt · arguments-*.json
  PACK-README.md
public/packs/packs.json          # manifest (File → Video packs… reads it)
```

Rebuild everything from gochema:

```bash
cd /root/manuscriptAI/deploy
./build-packs.sh                    # all packs + manifest
python3 make-pack.py <slug> <essay-dir> --title "…" --blurb "…"   # one pack
```

The argument graphs come from gochema `tools/argue-extract.py` (logicvid
sessions → nodes/edges JSON); drop them in `<essay>/arguments/*.json`.

## The AI copilot (what's under the hood)

- **Compiler-law prompt** is the chat's system prompt (Settings → custom
  prompts — user-editable). Packing sources auto-attached by rank:
  WEAVE → TAKES/JOURNEY → resources → quotes; whole files only (never
  truncated mid-quote); user picks override.
- **/sweep** — 4-section contract: Verdicts · READ checks · Implications ·
  Drafts (≤3). Auto-attaches pack sources when none picked.
- **Tools** the chat can call: `web_search` (DuckDuckGo via worker),
  `lookup_quote` (verbatim WEAVE grep), `verify_claim` (claim vs sources),
  `board_check` (storyboard clocks), `search_literature`, `read_section`.
- **Model**: any OpenAI-compatible endpoint via worker `/v1/chat/completions`
  (key lives in worker secret `OC_API_KEY`; default `longcat-2.5-preview-free`).

## MCP server (drive quill from any MCP client)

```bash
python3 /root/manuscriptAI/deploy/quill_mcp.py   # stdio
```

12 tools: `packs_list · pack_get · pack_source · sweep · verify_claim ·
lookup_quote · boardcheck · web_search · canon_search · canon_read ·
canon_verify · parallel_args` (canon = FoJin cross-canonical Buddhist
texts with portable URNs). Registered in `~/.config/opencode/opencode.jsonc`
alongside `fojin`. Tests: `python3 deploy/test_quill_mcp.py [--fast]` —
expect **13/13**.

## The autonomous runtime

```bash
python3 deploy/essay_runtime.py --pack what-is-jhana \
  --phases enquiry,draft,deslop,push,gate,storyboard [--chapter COLD]
```

Loop per chapter: **draft** (Go API) → **deslop** (deterministic:
not-X-but-Y, inflated vocab, filler openers — quote/owner blocks are
byte-protected) → **push** (logicvid formula: objection → answer from
banked sources → resolution → honest remainder) → **gate** (noslop
classifier, AI-conf < 0.20; KB-guided rewrite if over) → **storyboard**.
Banked-prediction-before-draft invariant (hloop). Outputs land in
`<essay>/RUNTIME-<ts>/` with `report.json`; never touches locked files
without `--promote`. Deslop port: eatusc-personal/no-slop (MIT) rules +
characters2 reflow defenses + noslop repair KB.

## Deploy stack

| Piece | What | Where |
|---|---|---|
| Worker | static assets + `/v1/chat` (Go key) + `/api/search` + bridge proxy | `deploy/worker.ts` · `wrangler.jsonc` |
| Bridge | TTS (phonon/fish) · yt-dlp · transcripts · render jobs | `deploy/bridge.py` · systemd `quill-bridge` |
| Tunnel | permanent `quill-bridge.agi.xn--q9jyb4c` ingress | systemd `named-tunnel` (see `deploy/BRIDGE.md`) |
| Secrets | `OC_API_KEY`, `BRIDGE_URL`, `BRIDGE_KEY` | `wrangler secret put …` |

```bash
cd deploy
export CLOUDFLARE_API_TOKEN=… CLOUDFLARE_ACCOUNT_ID=…
WEB=1 npm run build && wrangler deploy --config wrangler.jsonc
```

**Phonon** (local voices): `~/.cargo/bin/ptts` + `/root/phonon/model-31m-en`
(q4k 54MB). `ptts --help`, voices: `--list-voices`. Used by Script ▶ render,
canvas ▷ render, and top-bar 🔊 — offline, free, ~5s/section. Fish stays as
the cloud fallback (engine dropdown).

## Development

```bash
npm run lint        # tsc --noEmit   (gate 1)
npx vitest run      # ~2060 tests     (gate 2 — see CLAUDE.md rules)
WEB=1 npm run build  # dist/          (gate 3)
```

House rules (from CLAUDE.md, still enforced): reachability rows for every
new guarded control; pack docx are build artifacts (gitignored); owner words
in gochema are append-only; no invented citations anywhere — SILENT beats
a guess.
