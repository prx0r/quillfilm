# INTEGRATIONS — open-source survey for quillfilm (2026-10-20)

Rule: only **permissive** licenses (MIT/Apache/BSD/MPL-file) may have
*code* enter quillfilm (upstream lineage is MIT; the site is hosted →
AGPL/network-copyleft is poison). Everything else = PATTERN / NOTE /
VALIDATION. Verified via GitHub API + license files this session.

## The three (owner table, verified)

| repo | license (verified) | verdict | notes |
|---|---|---|---|
| **skyphusion-labs/vivijure** (+ -cf, -local, -core, -mcp, slate) | **AGPL-3.0-only** ✓ (LICENSE in repo) | **VALIDATION, not fork** ✓ | Independent confirmation of OUR architecture: control panel on Cloudflare Workers free tier **or** home box (Node/SQLite/S3), shared core lib, plus an **MCP server to drive the studio API from an agent** (→ same shape as our quill↔bridge plan). Bonus read: `vivijure-module/2` typed hook contract = our pack/bridge idea. AGPL + GPU renderers we can't touch → zero code. |
| **mainza-ai/milimovideo** | **claimed Apache-2.0 in README, but NO LICENSE FILE exists** (404; root has none) ⚠ | **PATTERN for board parser** ✓ (even stricter than thought) | ScriptParser regex idea: screenplay text → Scenes → Shots; ElementManager `@Element` conditioning; AI-parse fallback (Gemma) when regex fails. Do NOT copy files — no license text shipped. Steal the *grammar*: our tables are the source of truth (`STORYBOARD.md` / `MOVIE.md` beat tables → shot rows). |
| **dramaclaw/dramaclaw** | **Elastic-2.0** ✓ (REUSE.toml aggregate `**` → Elastic-2.0.txt; Apache-2.0 only for bundled OpenAI sandbox binaries) | **NOTE only** ✓ | Gateway sibling **dramaclaw-gateway is AGPL-3.0** (verified) → also unusable. OpenAI-compatible-gateway *pattern* only; our Go-proxy already is that shape. 6.4k★ but Elastic + drama focus = no reuse. |

## New finds — permissive, actually usable

| repo | license | what it gives us | use |
|---|---|---|---|
| **wassermanproductions/scriptbreak** | **Apache-2.0** ✓ | Offline (no phone-home) screenplay breakdown: scenes, elements, characters, locations, shot lists, timeline + **export "prompt packs" for any LLM/video gen** | Closest product fit in the survey: study its breakdown model + prompt-pack export as the shape of quillfilm's `STORYBOARD.md` → shot rows → render prompts. Code vendorable. |
| **reaink/script2video** | **MIT** ✓ | The *assembly + timing layer*: markdown script → shots → narration, word-accurate captions, backdrops, transitions, **deterministic encode** to mp4 | The timing/narration pass we'll need after the board approves. MIT → copy freely. |
| **zenstory-ai/drama-skills** | **MIT** ✓ | Claude-Code/Codex skill pack: script, character assets, **storyboard + image/video prompt skills**, review | Pattern (or direct source) for *film skills* files living beside WEAVE — the copilot's board-side instructions. |
| **62656456/ai-film-skills** | **Apache-2.0** ✓ | 21 modules: story, directing, visual assets, AI-film production, research galleries, **playable 3D previs** | The 3D-previs module = reference for the zone diorama stage (later). Apache → usable. |
| **piersdeseilligny/betterfountain** | **MIT** ✓ | Complete Fountain parsing/formatting in TypeScript (VS Code app) | If we ever import/export `.fountain`, mine its grammar; also a model of a focused writing tool. |
| **oparaskos/fountain-parser** | **MPL-2.0** | Fountain parser (small) | File-level copyleft: usable with attribution if files kept MPL. Prefer betterfountain (MIT) first. |
| **LingyiChen-AI/AIComicBuilder** | **Apache-2.0** ✓ (1.9k★) | Panel-based storyboard builder | Still-panel generation flow — candidate for the stills pass. Evaluate fit later. |
| **ifrost/afterwriting-labs** | **NO LICENSE** ⚠ | Fountain post-processing incl. **timing/page stats** | PATTERN only — its timing math (scene/shot duration estimation) is the idea for our `est t` column. Never copy code. |

## External (SaaS, non-OSS) — pattern watch only
- **ScreenWeaver** (Oct 2026): AI previz as 3D blocking panels +
  shot-value/camera-move-per-row sequencer → borrow the *column grammar*
  for STORYBOARD rows when we add camera metadata.
- **Storytella / Katalist / M Studio / Higgsfield**: entity-consistency
  + script→board pipelines → if we ever want painterly stills without
  our own render pass, these are the outsides.
- **Vivijure Slate**: Discord co-writer maintaining a machine-readable
  storyboard in background → validation that narrative → structured
  brief is the right loop (that's quill chat → WEAVE/STORYBOARD).

## Explicit DON'Ts
- No AGPL: vivijure family, dramaclaw-gateway, (anything skyphusion).
- No Elastic: dramaclaw code (gateway is AGPL anyway).
- No unlicensed copying: milimovideo (README claim, no LICENSE),
  afterwriting-labs, SKRIPTON (appears to be a scriptbreak-like app,
  unverified license — avoid until checked).
- Blender: GPL *application* — fine to drive headless for assets; never
  link its code into quillfilm.

## Next actions (board stage)
1. ✅ **done** — Beat-table parser: `board_parse` + `board_validate` in
   `deploy/quill_mcp.py` (our own table shapes: milimovideo pattern,
   scriptbreak model) → shot rows + structural validation (WEAVE refs,
   bells, timings). Tests 17/17.
2. Board-side copilot skills: adapt drama-skills (MIT) structure next
   to WEAVE — "storyboard", "shot prompt", "narration pick" skills.
   (`quote_for_row` is the deterministic first half; skill = the prompt
   layer on top.)
3. Timing pass: afterwriting-labs-style duration estimates → fill
   `est t` for A3/A4 rows (`board_validate` already reports untimed
   rows and flags out-of-order clocks).
4. Render bridge (post-board): script2video's deterministic-encode
   discipline + our bridge `/api/tts`; worker/home-box shape = the
   vivijure-validated path (Go proxy already matches).
