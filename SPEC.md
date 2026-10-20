# SPEC — Quill Copilot: ambient grounding agent + storyboard-to-render loop
> Status: DRAFT v0.1 (2026-10-20). Owner vision verbatim in VISION.md.
> Rule for this document: every external claim carries its exact quote.

## 1. What it is (one paragraph)
Quill is a **copilot video-generation loop**, not a video generator: the
owner writes, an ambient agent polls the draft, retrieves relevant
evidence (quotes, takes, clips) from per-video packs, structures findings
against the owner's own past videos, and feeds back **structured data**
(verdicts, quote-fixes, implication maps, storyboard rows) — it never
writes prose. Sections get marked done and rendered while writing
continues; agents render scenes in realtime under owner-set rules. The
enquiry becomes the video being made.

## 2. The loop (normative — this is the product)
1. **Owner writes** in the editor (voice inviolable).
2. **Agent polls** (on demand now; ambient later): takes the draft +
   attached pack sources as context.
3. **Retrieve**: verbatim quotes (WEAVE IDs), takes (TAKES.md), clips
   (CLIPS rows), prior-video structures (how the owner structured rebirth
   v1 → apply the recipe, don't invent one).
4. **Structure, don't author**: output = suggestion cards, READ-corrections
   ("manuscript says X, source says Y"), implication maps
   (verdict → crux → evidence → forward-link → next question), storyboard
   rows (shot, timestamp, visual, DIR).
5. **Owner marks sections done → render queue** builds scenes while writing
   continues; per-scene mods re-render in place.
6. **Every question asked becomes a JOURNEY.md row** — the film's spine is
   the owner's actual question chain, in order.

## 3. What's proven (in this repo, working today)
- Manuscript + attached sources in chat; compiler-law system prompt baked in.
- Packs: one film = one manuscript + evidence bank, one-click load
  (File → Video packs…), 22 packs live.
- Claim-verify against loaded sources; web_search tool via worker proxy.
- Worker holds keys server-side; bridge service pattern for box-side tools
  (yt-dlp/transcripts/clips) behind auth + tunnel.
- Deterministic render discipline exists downstream (hyperframes seek(t),
  PIL staged pipeline with gates — gochema series/BUILD-PIPELINE.md).

## 4. The landscape (exact quotes — nothing here does the loop)
**Generative UI (the analogy — confirmed real genre):**
- wandb/openui: "It's like v0 but open source" — "describe UI using your
  imagination, then see it rendered live."
- heldernoid/openstitch: "Draw cool web UIs with local LLMs… Text → UI…
  Sketch → UI… Infinite canvas - arrange screens spatially… No cloud
  required." (Closest analogy: canvas + generation + local. Still UI
  output, still writes the artifact for you.)
- ambitresearch/genie: "AI UI-component generation, inside your coding
  agent, against your own UI kit… No separate app to open" — the
  anti-app instinct we share, but for code components.
- Also: v0.diy, windai, grills, synth-ui, Helix (all v0-clones: prompt →
  component + preview).

**Copilot video generation (the genre — confirmed crowded, all authoring):**
- bluefish2026/BlueFish: "**An open-source AI storyboard & video
  generation studio.** Go from script -> storyboard -> generated video in
  a single web UI" + "Mock mode - run the full UI without any paid API
  keys" + "Provider adapter pattern - add a new video model by
  implementing one interface."
- seme-org/open-director: "An open-source AI video studio with a 9-agent
  director pipeline — from a one-line idea to a fully rendered video" —
  "Research Agent --> Script Agent --> Art Style Agent --> Storyboard
  Agent --> … --> Render Worker". (Closest pipeline shape. Differences:
  agents WRITE the script; no evidence bank; no compiler law; no
  question-chain.)
- Forget-C/Jellyfish (6.7k★): "From script input to structured
  storyboarding, consistency management, shot preparation, video
  generation, and export" + "Handle long-running generation as trackable
  tasks… status, cancel, and recovery."
- ChrisChen667788/wind-comic: "real-time multiplayer timeline to edit
  with your team like Figma for film."
- mainza-ai/milimovideo: "full **Non-Linear Editor (NLE)**" + "Script-to-
  Video: Paste standard screenplay text — Milimo parses it into Scenes
  and Shots."
- dramaclaw (6.3k★): "script to finished film in one pipeline" via
  "OpenAI-compatible gateway… Nothing runs models on your machine."
- skyphusion-labs/vivijure (AGPL): "Write a storyboard. Render it to video
  on your own GPU… Run the control panel on the Cloudflare Workers free
  tier… or on a home computer." (Closest ARCHITECTURE to ours: worker
  panel + home GPU. Differences: no grounded agent, no packs, no
  question-chain.)
- zedarvates/StoryCore-Engine: "Master Coherence Sheet ensures consistent
  style… Total Recall (Living Protocol): persistent neural memory."

**Grounded answering (half our loop):** NotebookLM ("operates only within
the boundaries of the sources uploaded by the user… direct quotes"),
Elicit/Consensus/scite (academic). **Script→video renderers (other half):**
Pictory ("edit the video like a document"), Kapwing ("chat to edit"
scenes), Steve.ai/explain.ink (whiteboard explainer style).

**The gap (why build):** nobody connects write → grounded-answer →
storyboard → render in one loop with the agent *forbidden from writing*.
NotebookLM can't storyboard; Pictory can't fact-check; Kapwing has no
quote discipline; open-director writes the script itself. Our moat is the
constraint set, not a feature.

## 5. Architecture (build on what exists)
```
EDITOR (quill, TipTap) — owner writes. Voice inviolable.
  │ draft + attached sources (verbatim context, 50k local budget)
  ▼
POLL AGENT (new) — on demand now (chat "sweep this section"), ambient later.
  │ tools: verify_claim (banked), web_search (worker /api/search),
  │        read_section, pack_lookup (WEAVE IDs), clip_search (bridge /api/yt)
  ▼ structured output only:
  ├─ suggestion cards (accept/reject → editor)
  ├─ READ-corrections ("ms X vs source Y" + verbatim fix)
  ├─ implication maps (verdict → crux → evidence → forward-link → next Q)
  └─ storyboard rows (shot/t0-t1/visual/DIR/audio) → BOARD VIEW (new)
BOARD VIEW (new) — shot table per chapter, statuses (draft/locked/
  rendering/done), per-scene mod → re-render single scene.
RENDER QUEUE (new) — deterministic jobs (hyperframes/PIL gates), status/
  cancel/retry (Jellyfish's async-task lesson), per-scene outputs.
CLIP INGEST (bridge, exists-as-shape) — /api/yt/*: meta/transcript/clip
  via yt-dlp + transcript API; needs cookies or unblocked box (BRIDGE.md).
PACKS (exist) — one film = manuscript + evidence; JOURNEY.md rows are the
  spine; TAKES.md is the research shelf.
```

## 6. Binding constraints (compiler law — non-negotiable)
1. Agent never writes owner voice. Drafts marked [DRAFT — owner to voice].
2. Every READ verbatim from a banked file (WEAVE ID + path). No quote
   without a source file in repo.
3. SILENT verdicts over invention. Unbanked claims flagged, never filled.
4. Owner's questions append to JOURNEY.md in order; never reordered.
5. One film = its pack's sources. No cross-pack contamination in chat.
6. No render without passing gates (sentence-match, drift, citations).

## 7. Phases
- **P0 SHIPPED:** editor + packs + compiler prompt + verify + web_search +
  worker proxy + bridge skeleton + 22 packs live.
- **P1 SHIPPED (2026-10-20):** `/sweep` slash-command → structured markdown
  (verdicts / READ-checks / implications / drafts); BOARD VIEW (shot-table
  parser, per-shot draft→locked→done, persisted, auto-built on pack load,
  md/JSON export); journey log + copy; `lookup_quote` + `clip_lookup` +
  `board_check` agent tools; bridge render jobs (submit/status/cancel per
  Jellyfish contract) with `boardcheck` provider proving board→job→result;
  provider plug-in interface for hyperframes/PIL. Gates: tsc + 2052 tests.
- **P2 (next):** render queue UI on bridge jobs; per-section render;
  hyperframes provider (SVG scenes via gcomedy stack); PIL stills provider.
- **P3:** clip ingest live (cookies/box) → transcript → timestamped rows
  auto-suggested into board slots; bridge on owner hardware.
- **Later:** ambient polling (interval + on-pause triggers), voice
  read-aloud of board rows, multi-film shared universe (WEAVE-GLOBAL).

## 8. Adopt, don't compete (owner ruling 2026-10-20 — verified per tool)

> Where a tool covers our need, we adopt its shape or its code. We build
> only what doesn't exist: the grounded loop (packs + compiler law +
> question-chain). Reason, stated once: **our renders are deterministic
> SVG/code (hyperframes seek(t), PIL staged gates), not generative AI
> video.** No studio below renders that. Their storyboard/queue SHAPES
> transfer; their renderers don't fit our visual grammar.

| Tool (license) | Verdict | What we take |
|---|---|---|
| BlueFish (Apache-2.0): "An open-source AI storyboard & video generation studio. Go from script -> storyboard -> generated video in a single web UI" | ADOPT PATTERN, not codebase | Provider adapter insight verbatim: "add a new video model by implementing one interface" → our render providers (boardcheck now, hyperframes/PIL next) implement one `render(job)` interface. Mock-mode precedent ("run the full UI without any paid API keys") justifies boardcheck-first. |
| Jellyfish (Apache-2.0, 6.7k★): "Handle long-running generation as trackable tasks… status, cancel, and recovery" | ADOPT CONTRACT | Bridge /render/* implements exactly this task contract (submit/status/cancel + log tail + result artifacts). We do NOT adopt its stack (MySQL/Redis/RustFS/docker) for a shot checklist — the contract transfers, the dependencies don't. |
| open-director (LGPL-3.0): 9-agent "from a one-line idea to a fully rendered video" | REJECT monolith, NOTE shape | Its stage order (Research → Script → … → Render Worker) validates our pipeline shape. Rejected as a unit: its Script Agent WRITES the script — direct compiler-law violation. Never wire idea-to-video recta. |
| wind-comic (MIT): "real-time multiplayer timeline to edit with your team like Figma for film" | INSPIRATION for board v2 | Single-owner v1 doesn't need multiplayer. Take the paradigm (timeline as the editing surface), defer the implementation. |
| Vivijure (AGPL-3.0): "Write a storyboard. Render it to video on your own GPU… Run the control panel on the Cloudflare Workers free tier… or on a home computer" | VALIDATION, not fork | This IS our architecture (worker panel + home-box bridge) — independent confirmation. Not forking: AGPL copyleft + AI-video renderers we can't use. |
| milimovideo (Apache-2.0): "Script-to-Video: Paste standard screenplay text — Milimo parses it into Scenes and Shots" | PATTERN for board parser | ScriptParser regex approach for STORYBOARD.md/MOVIE.md beat tables → our shot rows. Same idea, our table shapes. |
| dramaclaw (Elastic-2.0): "script to finished film in one pipeline" via "OpenAI-compatible gateway" | NOTE only | Gateway pattern matches our Go-proxy shape. Elastic license + drama focus = no code reuse. |
| NotebookLM / Elicit / Consensus | CLOSED or academic-only; no storyboard, no render | Nothing to adopt; they define the half-loop we complete. |

Rule for future tools: if it renders deterministic motion-graphics from
code behind an adapter interface, evaluate forking it. If it renders AI
video from prompts, take at most its queue/board shapes.

## 9. Arguments view (generative UI — owner brief 2026-10-20)

> The blank page becomes an argument map: as the owner writes, for/against
> branches appear beside the text; clicking a node streams its reasoning
> (typewriter reveal per Upstash smooth-stream pattern), speaks it in its
> character's voice (Fish), and offers forward links (next enquiries).
> Demo live: `/demo/karma-satsang/` (karma chain, 3 voices, KaTeX domino).

**Adopt verdicts (exact quotes):**
- Argdown (MIT, 1k★): *"Argdown is a simple syntax for analyzing complex
  argumentation"* + *"Argdown can even be used within Markdown… Your code
  is transformed into an argument map while you are typing."* → ADOPT the
  pattern (markdown-native, transforms-while-typing). Our argue-extract.py
  already parses session markdown into graphs; Argdown syntax is the v2
  authoring format candidate.
- reasons/davekinkead (MIT): *"Nodes and edges are plain javascript objects"*
  → ADOPT the shape: our argument JSON already is {id,text}+{from,to,rel}.
  No new renderer needed for v1 (nested styled lists); reasons.js canvas is
  the v2 option.
- ClaimGraph principles (proprietary — principles only, never code):
  *"1. The graph is the product; it is not a chat transcript. 2. Every
  substantive node must have provenance… 5. Missing evidence and unresolved
  assumptions are first-class graph nodes… 7. Layout is deterministic
  application code, not generated coordinates."* → ADOPTED as our graph
  laws (provenance per node, gap nodes, deterministic layout).
- doubt (MIT): *"Refuses evidence without a bounded source region"* +
  typed supports/contradicts/qualifies/missing edges → ADOPT the evidence
  contract (our rel set maps 1:1; add `qualifies`).
- Premise (MIT): *"Typed argument nodes"* + *"crux nodes highlighted"* +
  *"AI argument classifier… degrades gracefully with no key"* → ADOPT node
  types + crux highlighting; classifier = our lookup_quote + sweep.
- debate-arena (MIT): *"Each claim is spoken via ElevenLabs as the LLM is
  still writing it: prose tokens feed a sentence chunker"* + per-agent
  voice map → ADOPT the pattern with Fish voices (demo does exactly this:
  sentences chunked per node, each node spoken in its character's voice).
- thesys/open-intelligent-ui (MIT, Oct 2026): *"answers stream as
  interactive UI (maps, photos, charts, drawings and working tools)"* +
  `Math` (KaTeX) + `Svg` primitives → ADOPT: our Arguments view IS an
  Intelligent-UI answer. KaTeX on the demo domino today, Svg scenes
  tomorrow via hyperframes.
- tension-map (MIT): *"Click a tension to see the shared premise keeping
  both sides plausible, and one open question"* → ADOPT the gap-node
  interaction (our honest-remainder nodes already carry this).

**Pushing algorithm = the generative core (confirmed):** the
pushing-tantraloka logicvid sessions ARE objection→answer+quotes→
resolution→honest-remainder chains (`argue-extract.py` parses 35 files
into argument graphs). JOURNEY.md chains are the same shape for karma.
Autocompletion = given any node, generate children: counterclaims (guard
patterns), quotes (lookup_quote), next questions (implications). The model
never writes; it extends the graph from banked evidence.

## 10. Primitives reuse + voice pipeline (owner brief 2026-10-20)

> Cloned: `/root/open-intelligent-ui` (thesysdev, MIT, Oct 2026). Take
> patterns, not the app: their stack (Next.js + OpenUI Gateway + AI video
> models) answers a different question than ours.

**What we lift, verbatim-shaped:**
- `Quote({text, cite})` — *"A quotation or a callout with a side rule;
  cite names the source."* → our READ cards, verbatim props, gold serif.
- `MathBlock({tex, inline})` — *"LaTeX formula"* rendered server-side via
  `katex.renderToString(..., {output: "htmlAndMathml"})` — *"KaTeX escapes
  its input"* → no client KaTeX needed; worker or build step can
  pre-render. Domino/formalizations render as HTML strings.
- Drawing set (`Svg/G/Circle/...` *"whose attributes take expressions"*,
  `HtmlView` sandbox) → the v2 Arguments canvas + hyperframes scenes:
  deterministic SVG from data, never model-drawn coordinates.
- `YouTube({video})` — nocookie embeds by ID only (*"Only a video you
  know exists"* — same honesty rule as our clip slots).
- Streaming doctrine (Upstash pattern, already adopted): buffer network
  chunks, rAF typewriter reveal. Worker `/v1/chat` currently buffers
  (`await upstream.text()`) — streaming passthrough is P1 work.

**Voice pipeline spec (P3 — text flow first, per owner):**
1. Preseed: load pack (exists). Preliminary extraction: sweep + boardcheck
   + argue-extract (exists) — the AI does its homework BEFORE dialogue.
2. Argue via text: chat with attached sources + web_search + lookup_quote
   (exists). The debate-arena pattern (*"Each claim is spoken… as the LLM
   is still writing it: prose tokens feed a sentence chunker"*) applies at
   render time, not chat time — paced debate is too slow for thinking.
3. Owner's voice becomes the reading voice: owner records the locked
   narration lines (phone mic is enough) → Fish voice-clone → narration
   rendered in owner's voice for prototypes; teacher/character voices
   (Louis/Ari/Casey clones banked) for dialogue scenes.
   VERIFY before build: Fish clone endpoint + quota (audition scripts
   cover synthesis, not cloning).
4. Satsang scene assembly: argument graph → nodes get voices (narrator =
   owner or Louis; skeptics = character clones) → per-node MP3s via
   bridge render job (`tts` provider — new, mirrors boardcheck pattern) →
   demo page already proves the player.

**Priority order (owner): text flow fluid first.** No voice/bridge work
until chat+sweep+board+arguments run clean in the browser.

## 11. Open questions (owner brief)
1. Polling trigger: manual command only, or ambient on-pause? (Start manual.)
2. Board view: new rail task or inside Write panel? (Done: Write panel section.)
3. Render engine for v1: hyperframes SVG scenes (deterministic, free) vs
   stock/AI footage (Pictory-style)? Owner's visual grammar says SVG-first.
4. Clip rights gates stay manual (ask-first clearances can't be automated).
5. Arguments canvas: nested lists (now) vs reasons.js/D3 canvas (v2)?
6. KaTeX in quill chat (deps) vs demo-only (CDN)? (Propose: demo now, app later.)
