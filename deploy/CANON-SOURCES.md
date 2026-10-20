# CANON-SOURCES — free-only text retrieval for the quill dialectic workflow
> Every source here is free, keyless (or anon-rate-limited), and citable to line.
> Purpose: rapid argument iteration — search canon, web, and pack in parallel,
> no bulk downloads (disk discipline: 4.7G free on /).

## MCP endpoints (configured in opencode.jsonc)

| Server | Endpoint | Auth | Status |
|---|---|---|---|
| **FoJin Buddhist** | `https://mcp.fojin.ai/mcp` (remote) | anon rate-limited | **LIVE — verified** |
| **quill** | `python3 /root/manuscriptAI/deploy/quill_mcp.py` (local stdio) | Go key + bridge key | **LIVE** |
| fish-audio | `https://api.fish.audio/mcp` (remote) | FISH_API_KEY | pre-existing |

### FoJin tools (8)
`search_corpus` (semantic, 10K+ texts, 30+ langs) · `read_passage` (by URN) ·
`get_parallels` (cross-canon: Chinese/Pali/Tibetan) · `lookup_dictionary` (32 dicts) ·
`lookup_entity` · `resolve_urn` · `verify_quote` · `commentaries`
Every hit carries a portable `fojin:` URN resolving to CBETA / SuttaCentral /
84000 / GRETIL numbering. Apache-2.0, read-only.

### quill tools (12)
`packs_list` · `pack_get` · `pack_source` · `sweep` (verdicts+READ+implications) ·
`verify_claim` (one claim vs pack sources) · `lookup_quote` (WEAVE ID grep) ·
`boardcheck` (storyboard clock validation) · **`canon_search`** (FoJin search) ·
**`canon_read`** (FoJin passage by URN) · **`canon_verify`** (FoJin quote verify) ·
**`parallel_args`** (canon + web + pack WEAVE in parallel, one query) ·
`web_search` (DuckDuckGo via bridge)

## Free API endpoints (no MCP, plain fetch)

### SuttaCentral API — Pali, English, cross-canon
- `https://suttacentral.net/api/suttaplex/{uid}` → blurb + translation list
- `https://suttacentral.net/api/suttas/{uid}/{author}` → segmented root + translation
- `https://suttacentral.net/api/parallels/{uid}` → cross-canon parallels
- CC0 code; roots public domain; check per-translation licence before rendering.
- Bilara data mirrors on GitHub for bulk (don't pull — disk).

### Scaife (Open Greek and Latin) — Greek, Latin
- `https://scaife.perseus.org/reader/{urn}` (human)
- `https://scaife.perseus.org/api/cts/?urn={urn}&format=xml` (machine)
- CTS URNs: `urn:cts:greekLit:tlg0557...` — citable to line, 2,699 works.
- Free, stable.

### OpenITI — Arabic, Islamicate
- GitHub org `OpenITI`, repos by 25-year death-date buckets (e.g. `0775AH`).
- Zenodo DOI `10.5281/zenodo.3082463` for citable releases.
- mARkdown scheme for structure; text-reuse TSVs for parallels.

### GRETIL — Sanskrit
- `http://gretil.sub.uni-goettingen.de/gretil.html` — cumulative zips, UTF-8.
- Standardize GRETIL as the Sanskrit pointer. (Also reachable via FoJin `lang=sa`.)

## What we deliberately did NOT pull (disk discipline)
- Tripitaka Pali local SQLite canon (~120MB) — FoJin hosted covers Pali.
- Bilara bulk mirrors — SuttaCentral API is enough for iteration.
- OpenITI full text repos — use Zenodo DOI releases selectively when needed.
- GRETIL cumulative zips — FoJin `lang=sa` for search; fetch individual files only.

## Parallel argument pattern (quill_mcp `parallel_args`)
One query → three simultaneous result sets:
1. **Pack WEAVE** — existing banked evidence (deterministic grep)
2. **Canon (FoJin)** — cross-canonical passages with URNs
3. **Web** — blogs, forums, teachers, specialists (DuckDuckGo via bridge)
Returns all three in one block. The agent reads them, picks the strongest
cites, and feeds them back into the argument graph (JOURNEY.md row).
