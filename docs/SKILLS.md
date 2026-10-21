# SKILLS.md — the nibbāna film workflow (reproducible)

How this film got made, from raw sermons to a live, editable, quote-safe
board. Written while hot (2026-10-20/21), to be followed again — on the
rest of this film, and on the next source. Everything here ran for real;
paths, numbers and commands are the actual ones.

**Current state:** 33 sermons excavated → 6-section scaffold → motif
world → film constitution (pointer/trojan) → WEAVE bank `[F1]–[F34]`
(verbatim) → 30 board rows (5 hook · 16 intro · 6 zones · 3 coda) →
SCREENPLAY stagewrite live in quillfilm → MCP tools 16 (tests 17/17) →
2 open [DRAFT] slots (I11, I4). Repos: `prx0r/satsang-extensions`
(packs 51–54) + `/home/ubuntu/quillfilm` (the desk).

---

## 0. The pipeline (map)

```
sermons (PDF→txt)                          satsang-extensions/53
  └─ 3-pass excavation ×33 (per-sermon files, 6 sections + satellites)
       └─ scaffold master (argument order)  53/nibbana-scaffold.md
            └─ motif mining (### headers = curated imagery)
                 └─ world bible (zones ↔ sections ↔ Nandi stages)   51/MOTIFS.md
                      └─ film constitution (thesis, laws, POINTER)  quillfilm MOVIE.md
                           └─ WEAVE bank (verbatim [F#] + cites)     quillfilm sources/WEAVE.md
                                └─ board rows (ids, times, bells)    quillfilm STORYBOARD.md
                                     └─ stagewrite (scene blocks)    quillfilm SCREENPLAY.md
                                          └─ MCP gate/loop tools     quillfilm deploy/quill_mcp.py
                                               └─ narration write → timing → stills → render (next)
```

Rule of the whole chain: **nothing enters the film that is not banked or
a marked render of something banked.** The validator enforces it.

---

## 1. SKILL: source excavation (raw → organized raw material)

**When:** any teaching text where everything useful must be extracted
before deciding what matters.

**Method (3 passes — full spec: satsang-extensions/54-excavation-skill/):**
1. **Pass 1 — full extraction.** Read the entire source. Extract every
   metaphor, argument, refutation, definition, citation, cross-reference,
   practice instruction, turn, and line worth keeping. Quote, don't
   paraphrase. Don't judge importance — compression comes later.
2. **Pass 2 — verify against source (adversarial).** Re-read in chunks;
   hunt what you missed; check every verse, Pali term, named person,
   sidebar; log misses in a `PASS 2 FINDS` section. If 0 misses, you
   didn't look hard enough.
3. **Pass 3 — hole hunting.** Not against the source: against the
   scaffold. Thin sections, missing links, connections to other sermons,
   Analayo parallels, pratikas. Note holes; never fill with invention.

**Output shape (per sermon):** the 6 scaffold sections + Refutations +
Evidence + Voice (verbatim keeper lines) + Pass 2 + Pass 3.

**Quality gate — the fidelity audit (what made this bank trustworthy):**
machine-check every quoted fragment against the raw text:
- normalize (curly quotes→straight, whitespace collapse, intra-word
  hyphens removed for PDF artifacts, casefold)
- split quotes on `...` ellipses; each fragment ≥40 chars must appear
  in the source OR score ≥0.92 similarity (`difflib.SequenceMatcher`
  sliding-window `quick_ratio`)
- every miss fixed in place AND logged in PASS 2 FINDS
- residual flags classified: header/table regex artifacts vs real
  defects (dropped words, spliced sentences, paraphrase-in-quotes,
  editorial labels inside quotes) — fix the real ones
Sermon 33 finished at **zero** low-similarity quotes. That is the bar.

**Also run:** pack validation `11-site-runtime/check_pack.py … --receipts`
(ALL PASS) per change; commit per sermon.

**Where:** `satsang-extensions/53-nibbana-scaffold/sermon-NN-excavation.md`
(1–33). Sources: `/tmp/opencode/nibbana/Nibbana-*.txt` (PDF→txt).

---

## 2. SKILL: scaffolding (disorder → argument order)

**When:** you have raw extracts and need the argument, not the source's
delivery order.

**Method:** build ONE master file of **6 sections** (not sermon order —
argument order):
1. What X is · 2. How the mechanism works · 3. What keeps it running ·
4. What the mechanism builds · 5. How to see through it · 6. What
remains
Each section: claims · key moves · which sources support it · evidence
(sutta + parallels) · what it refutes · visual · direct-experience test.
Plus the master one-paragraph argument and the flow list.

Every excavation file is **pre-sorted into the same 6 sections** so raw
material is keyed to the scaffold. Satellites that sit outside the 6
(refutations, evidence, voice, pass 2/3) fold back into the sections at
merge time.

**Where:** `satsang-extensions/53-nibbana-scaffold/nibbana-scaffold.md`.

---

## 3. SKILL: motif & world mining (images → anchors)

**When:** the film must be memorable as *tropes*, so contemplations
return in daily life as jolts.

**Method:**
- The curated `###` subsection headers in the excavations ARE the motif
  inventory. Mine them (don't re-grep prose).
- Rank by recurrence across sources × jolt-power (daily-life trigger) ×
  cinematic renderability. Pick ~12 anchors.
- Build ONE diorama world where every motif has a physical home; lay
  the world out as the argument (river-to-sea transect = sections 1→6).
- Map zones ↔ scaffold sections ↔ sibling products (game stages,
  practice cards).
- One **bell** per motif introduction (audio cue); every later ring of
  that bell = the contemplation jolt. Bells never re-introduce.
- Bank each anchor's best verbatim line with source number.

**Where:** `satsang-extensions/51-nibbana-movie/MOTIFS.md` (world bible
incl. thesis); zone table + stage map. Result here: 12 anchors, e.g.
fire (motif 1), sandcastle, vortex, pixels, mirror, dog-on-plank, magic
show, chess, razor, raft, knots, lotus.

---

## 4. SKILL: the pointer (meta angle — content expressed as form)

**When:** the film's subject is perception itself, so the medium must
carry the message.

**Constitution (in MOVIE.md — edit there, obey here):**
- **Thesis:** the mind creates the movie. If there is no movie — what
  is there? Ground in quotes: the spectator makes the show [F1]; no
  cinema ever showed a film, yet it was seen [F2]; no first beginning
  in a cycle [F4]; know-all, stand nowhere [F5].
- **Structural laws:** 1 no progression (arrivals at beginnings; loop)
  · 2 no resolution (cessation not conclusion; last bell just stops) ·
  3 no time (present-tense; cycle; holds expose stills) · 4 **the
  spectator is the subject** (words about the screen until they are
  about you — never announced).
- **POINTER / trojan:** the whole film is a pointer/meditation
  disguised as a film. Narrator = the teacher (his words only). The
  realization is allowed to land anywhere; the first stab is the hook's
  BLACK SCREEN / AUDIO ONLY (the audience described over your own
  dark room). **If a line explains the trick, cut the line.**
- **Hook architecture (rows H1–H5):** radio invite (vow as invitation)
  → show that pixelates apart → two-voice interrogation (banked
  dialogue) → pure-audio penetration → breath into the prologue. Loop
  target = H1: the question re-asks itself; the film never began.
- **Sound:** score blends into reality (everyday sound; birdsong
  crossing into music). Silence is a rhythm; HOLD ≥8s = bed only.

**Narration engine:** verbatim `[F#]` or close plain-English **render**
of his words (`[RENDER — S#]`; e.g. papañca → spiralling/proliferation/
elaboration). No invented doctrine; other teachers do not appear; owner
glue only as last resort, marked `[DRAFT]`. Recorded-sermon voice is
the intended narrator track (verify audio rights before any cut).

---

## 5. SKILL: WEAVE banking (the quote bank — the film's only evidence)

**Format (one entry per line block):**
`**[F7] Ñāṇananda, S1** — "verbatim…" — cite — STOP <row/beat>.`
- IDs unique per pack (F#, K#, …). Voice = source + sermon number.
- Verify EVERY line against the raw source before banking (see §1
  fidelity audit). Whitespace/hyphenation artifacts may be normalized;
  words may never be.
- STOP = where it's allowed to appear (row id or beat).
- Spares allowed (STOP spare) for later rows.
- Parser: `deploy/quill_mcp.py _weave_entries` (wrapped lines joined;
  first `"…"` = quote; text to STOP = cite). Keep entries single-block.

**Where:** `quillfilm/public/packs/<slug>/sources/WEAVE.md`. This pack:
[F1]–[F34].

---

## 6. SKILL: board & screenplay (bank → rows → stagewrite)

**Board = record.** `STORYBOARD.md` tables, one act per `##` heading:
`| id | est t | scene (still) | narration [F#]/[DRAFT] | bell |`
- Row ids stable forever (I1…, H1…, Z1…, E1…) — the join key across
  board, screenplay, stills, render.
- Timings `m:ss–m:ss` or `tbd`; bells `BELL X`; silence = `—` (legal).
- Hook rows first (A-1), then intro, zones (mapped to the 6 sections),
  coda. Loop marker documented; total hook runtime noted for the
  timing pass.

**Screenplay = writing surface.** `SCREENPLAY.md` first in the
manuscript manifest so `?canvas=<slug>` places its `##` chapters as
movable objects (prologue + 6 sections + coda + rhythm map + flags).
Scene blocks keyed to row IDs: ACTION · RHYTHM · NARRATION · NOTE.
Rhythm vocabulary: HOLD · PUSH · DRIFT · NO CUTS · BELL+HOLD · LOOP ·
STEPPED · AUDIO ONLY. Rhythm lives in the screenplay, not the board.

**Gates before writing:** `board_validate` (WEAVE refs exist, unique
ids, bell inventory incl. multi-bell cells, timing format/order,
counts) — errors block; warnings (untimed rows) are legal until the
timing pass.

**Where:** `quillfilm/public/packs/nibbana-movie/manuscripts/`.

---

## 7. SKILL: combinatorial narrative (how it composes)

The film is assembled, not improvised:
- **Units:** banked quotes (34) + renders (unbounded but rule-bound)
  + silence.
- **Slots:** board rows (30). Each slot accepts any banked unit whose
  STOP allows it (validator enforces existence; STOP is editorial law).
- **Composition loop (deterministic tools, no LLM needed):**
  1. `board_parse` → see the rows
  2. `quote_for_row(row_id=…)` → assigned quote + best banked matches
     by keyword overlap (SILENT if nothing — then either write a render
     from a sermon line or bank a new [F#] via the §1→§5 pipeline)
  3. set the cell → `board_validate` → PASS required
  4. stage-write the scene in SCREENPLAY (rhythm + action around the
     locked narration)
- **Why it stays safe:** a missing ID is an ERROR (not a guess); a
  paraphrase must be marked `[RENDER — S#]` and derived from a real
  line; the compiler law (never invent citations/numbers/terms) applies
  to every copilot reply in the editor too.
- This is combinatorial in the strict sense: narrative = selections
  from a verified set under structural constraints (bells, laws,
  rhythm). New meaning comes from **juxtaposition**, not new sentences.

---

## 8. SKILL: MCP flow (the desk's hands)

**Server:** `deploy/quill_mcp.py` (stdio; FastMCP = **mcp<2**, pinned
venv: `python3 -m venv .venv && .venv/bin/pip install -r
deploy/requirements.txt`).
**16 tools:** packs_list · pack_get · pack_source · sweep ·
verify_claim · lookup_quote · boardcheck · web_search · canon_search ·
canon_read · canon_verify · parallel_args · **board_parse ·
board_validate · quote_for_row · movie_outline**.
- Board tools are deterministic/local; `boardcheck`/`web_search` need
  the bridge; `sweep`/`verify_claim` need the Go API; canon_* = FoJin
  (works).
**Tests:** `.venv/bin/python deploy/test_quill_mcp.py --fast` → expect
**17/17** (bridge tools self-skip offline). Update the expected tool
set + row-count assertions whenever the pack grows.

---

## 9. Reproduction checklist (new source → live board)

1. Source → txt; run §1 excavation per unit (pass 1–3 + fidelity audit
   + pack check; commit per unit).
2. Build/extend the §2 scaffold (6 sections) for that source's key
   claim; pre-sort every excavation into it.
3. Mine motifs (§3): rank headers, pick anchors, design one world,
   assign bells.
4. Write the film constitution (§4): thesis grounded in quotes, laws,
   POINTER/trojan, hook architecture, sound principle. Narrator = the
   teacher's words only.
5. Bank WEAVE (§5): best lines per anchor + hook + spares; verify
   every line.
6. Board rows (§6): hook → intro → zones(=sections) → coda; ids,
   times, bells; `board_validate` PASS.
7. Stagewrite SCREENPLAY (§6): scene blocks, rhythm, notes; register
   first in packs.json (canvas chapters).
8. Composition loop (§7) until every row has banked narration; only
   then timing pass → stills → render.
9. Log progress in this file's §11 and commit at each gate.

---

## 10. Progress log

- 2026-10-20: packs 42–54 live (excavation skill, scaffold, 33 sermon
  excavations ALL PASS; fidelity audits; motif mining; world bible;
  moviedraft intro verbatim).
- 2026-10-20/21: quillfilm fork (bd80e5e) · INTEGRATIONS survey
  (9a3a9b5) · MCP board tools, tests 17/17 (ca611e8) · SCREENPLAY live
  (f7dc55b) · HOOK + law 4 (586955d) · deep-bank F26–F34 + words-only
  narration swap (after that commit) · POINTER constitution (f3f0bb3).
- Open: I11 opening-line pick · I4 rarity beat (lotus/turtle/line) ·
  A3/A4 narration writing (renders) · timing pass · audio-rights check
  for recorded sermons · puppet/beams spares as rows thicken.

## 10b. Progress log (continued)

- 2026-10-21: two-films split (FILMS.md) · FORMULA (owner chain +
  substitutions + stream entry + cameras) · SECTIONS (six under the
  avijjā/vijjā binary + THE INVISIBILITY TRICK) · grab.html realtime
  model · THE LOOP format (5 passes, full encapsulation by .4) ·
  COURSE (five movements, chain-verified 22+/33 continuations) ·
  RAMP (165 blocks, mN.1–mN.5, cross-audited: 0 sub-0.90) ·
  MAP (25 verbatim units, recombine-never-rewrite) · WEAVE now F1–F46
  (11 banked raw-verified this session) · LESSONS index (33 rows) ·
  INVISIBILITY.md (the definition) · VALIDATION (five houses).

## 11. Next steps (board stage, in order)

1. Close the two [DRAFT] slots (I11, I4) from the bank.
2. Write A3/A4 narration via §7 (renders where the bank is thin —
   especially Z4a texture, courtyard).
3. Timing pass → STORYBOARD `tbd` filled → `boardcheck` clocks.
4. Stills per row (one held frame; look = stop-motion diorama).
5. Rights check on sermon recordings → narrator track.
