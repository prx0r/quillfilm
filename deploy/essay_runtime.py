#!/usr/bin/env python3
"""essay_runtime.py — autonomous essay-writing runtime for gochema videos.

The loop (fused from 3 owner repos + the pushing formula):

  ENQUIRY  → question chain from STRUCTURE.md (Go API, pushing prompt)
  DRAFT    → chapter prose (Go API, compiler law + owner voice ref)
  PUSH     → objections/resolutions/remainders per chapter (Go API,
             logicvid formula: question → answer+quotes → resolution → gap)
  GATE     → noslop classifier local (no API): AI-conf must be < 0.20
             if over: diagnose (detector) → rewrite (Go API) → re-measure
             (characters2/reflow pattern: classifier is the objective)
  STORYBOARD → shot rows from final chapters (deterministic template)
  REPORT   → manifest with every score (influence/hloop: bank prediction
             BEFORE drafting, record actual after gating)

Run:  python3 essay_runtime.py --pack what-is-jhana [--phases enquiry,draft,push,gate,storyboard] [--chapter "CH.1"]
Outputs: <essay-dir>/RUNTIME-<timestamp>/ with ESSAY-draft.md, PUSHBACK.md,
STORYBOARD.md, report.json. Does NOT overwrite locked files (ESSAY.md,
draft1.md) until --promote is passed.

Voes nothing that touches money beyond the Go API (free tier).
"""
import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone

# --- config ---------------------------------------------------------------
PACKS_DIR = '/root/manuscriptAI/public/packs'
GO_URL = 'https://opencode.ai/zen/go/v1/chat/completions'
GO_MODEL = os.environ.get('OPENCODE_GO_MODEL', 'longcat-2.5-preview-free')
NOSLOP_SRC = '/root/noslop/miner/src'
SLOP_TARGET = 0.20  # characters2/reflow TARGET
MAX_GATE_ITERS = 3

sys.path.insert(0, NOSLOP_SRC)
from classifier import classify  # noqa: E402
from detector import detect      # noqa: E402
from knowledge import glossary   # noqa: E402 — pattern KB: why_slop/repairs/rules


def go_key():
    # File first (fresh — shell env may hold an expired key), env as fallback.
    try:
        for line in open('/root/.hermes/profiles/builder/.env'):
            if line.startswith('OPENCODE_GO_API_KEY='):
                k = line.strip().split('=', 1)[1]
                if k.startswith('oc_sk_') or k.startswith('sk-'):
                    return k
    except OSError:
        pass
    k = os.environ.get('OPENCODE_GO_API_KEY', '')
    if k:
        return k
    raise RuntimeError('no Go API key')


def go_chat(system, user, max_tokens=4096, temperature=0.4):
    import urllib.request
    body = json.dumps({
        'model': GO_MODEL,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'temperature': temperature, 'max_tokens': max_tokens,
        'enable_thinking': False, 'think': False,
        'chat_template_kwargs': {'enable_thinking': False},
    }).encode()
    req = urllib.request.Request(GO_URL, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {go_key()}',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
        'x-opencode-session': str(uuid.uuid4())})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    try:
        return d['choices'][0]['message'].get('content') or ''
    except (KeyError, IndexError):
        raise RuntimeError(f'Go API error: {json.dumps(d)[:400]}')


COMPILER = """You are the owner's script COMPILER for gochema essay-films. Rules:
1. You COMPILE, never author. Owner words are immutable. New narration you draft must be marked [DRAFT — owner to voice].
2. [READ — cite] lines must be verbatim from sources attached. If unsure of wording, write SILENT and name which source to check.
3. Never invent citations, numbers, dates, or quotes.
4. Voice: short, dry, direct. No AI-slop (no "delve", "tapestry", "it's important to note", no three-list clichés, no "not merely X but Y" negations).
5. Include > DIR: stage/visual direction where a beat needs one."""


# --- deterministic deslop (ported rules: eatusc-personal/no-slop, MIT) -----
# Mechanical slop (filler openers, inflated words, hype phrases, em-dashes)
# is removed by string work BEFORE any LLM rewrite: instant, idempotent,
# can't invent slop of its own. LLM rewrite only sees what survives.
PROTECTED = ('[owner', '[read', '> dir', '##', '```', '|')  # prefixes never touched
CONTAINS = ('[read', '[owner', ' dir:')  # mid-line markers also protect the line
EM_DASH_KEEP = re.compile(r'(\d)\s*[–—]\s*(\d)')

WORD_SWAPS = [
    ('delve into', 'look at'), ('delving into', 'looking at'), ('delves into', 'looks at'),
    ('delve', 'dig'), ('delves', 'digs'), ('leverage', 'use'), ('leveraging', 'using'),
    ('utilize', 'use'), ('utilizing', 'using'), ('utilization', 'use'), ('facilitate', 'help'),
    ('endeavor', 'try'), ('commence', 'start'), ('elevate', 'improve'),
    ('underscore', 'highlight'), ('foster', 'build'), ('garner', 'get'),
    ('showcase', 'show'), ('a myriad of', 'many'), ('myriad of', 'many'), ('myriad', 'many'),
    ('a plethora of', 'plenty of'), ('plethora of', 'plenty of'), ('plethora', 'plenty'),
    ('robust', 'solid'), ('seamless', 'smooth'), ('vibrant', 'lively'), ('bustling', 'busy'),
    ('meticulous', 'careful'), ('cutting-edge', 'advanced'), ('state-of-the-art', 'advanced'),
    ('game-changer', 'big deal'), ('paradigm shift', 'shift'), ('synergy', 'teamwork'),
    ('holistic', 'complete'), ('pivotal', 'key'), ('crucial', 'key'), ('essence', 'core'),
    ('ever-evolving', 'changing'), ('unprecedented', 'rare'), ('transformative', 'major'),
    ('embark on', 'start'), ('embark', 'start'), ('harness', 'use'),
    ('streamline', 'simplify'),
]
PHRASE_SWAPS = [
    (re.compile(r'\brich tapestry of\b|\btapestry of\b', re.I), ''),
    (re.compile(r'\bin the realm of\b', re.I), 'in'),
    (re.compile(r'\bnavigating the (?:complexities|landscape|world) of\b', re.I), 'handling'),
    (re.compile(r'\bstands? as a testament to\b', re.I), 'shows'),
    (re.compile(r'\bis a testament to\b', re.I), 'shows'),
    (re.compile(r'\ba testament to\b', re.I), 'proof of'),
    (re.compile(r'\bplays? a (?:crucial|vital|key|pivotal) role in\b', re.I), 'is key to'),
    (re.compile(r"\bin today's (?:rapidly |fast[- ])?(?:evolving|fast-paced|changing|dynamic)(?: world| landscape)?\b", re.I), ''),
]
OPENERS = [
    re.compile(r"\bit'?s important to (?:note|remember|understand|mention|consider) that\b", re.I),
    re.compile(r'\bit is important to (?:note|remember|understand|mention|consider) that\b', re.I),
    re.compile(r"\bit(?:'s| is) worth (?:noting|mentioning) that\b", re.I),
    re.compile(r'\bit should be noted that\b', re.I),
    re.compile(r'\bneedless to say,?\s*', re.I), re.compile(r'\bat the end of the day,?\s*', re.I),
    re.compile(r'\bthat being said,?\s*', re.I), re.compile(r'\bin conclusion,?\s*', re.I),
    re.compile(r'\bin summary,?\s*', re.I), re.compile(r'\ball in all,?\s*', re.I),
    re.compile(r'\bwhen it comes to\b', re.I),
    re.compile(r'\bas (?:we|you) (?:can|could|will|would|may|might) (?:see|navigate|explore)\b[^,.]*,?\s*', re.I),
]
TRANSITIONS = re.compile(
    r'(^|[.!?]\s+|\n)(?:Furthermore|Moreover|Additionally|Notably|Importantly|Indeed|Essentially|Ultimately|Consequently|Subsequently),?\s+',
    re.M)

# NEG defenses (port from characters2/reflow break_neg+break_copula, SAFE subset).
# The rule from noslop KB: "State what it IS. No negation." — deterministic
# only where meaning provably survives (Y is the positive claim, kept in place).
# Anything tighter (modal negation, "not that X but Y" qualification) is left
# for the gate rewrite with the KB repairs — never mechanically stripped.
# "… not OBJ_A, but OBJ_B." → keep OBJ_B (propagating prep: "is not about X,
# but Y" → "is about Y"). Sentence-initial "Not X, but Y" (no subject before)
# is left for the gate — mechanical drop would orphan the predicate.
# Rule from noslop KB: "State what it IS. No negation."
NEG_DROP = re.compile(r'\bnot ([^,.!?]+?)\s*,?\s+but\s+([^,.!?]+?)([.!?]|$)', re.I | re.M)
_NEG_PREPS = ('about', 'for', 'with', 'of', 'to', 'in', 'by', 'from', 'on')
# "It's not X. It's Y." / "They are not X. They are Y." → keep the IS-statement
NEG_COPULA = re.compile(
    r"\b(It|That|This|He|She|We|They)('s|s| is| are|'re| am) not ([^.!?]+?)\. "
    r"\1('s|s| is| are|'re| am) ([^.!?]+?)\.", re.I)


def _neg_repl(m):
    obj_a, obj_b, term = m.group(1), m.group(2).strip(), m.group(3) or ''
    lead = re.match(r'\b(' + '|'.join(_NEG_PREPS) + r')\b\s*', obj_a, re.I)
    if lead and not re.match(r'\b' + re.escape(lead.group(1)) + r'\b', obj_b, re.I):
        obj_b = lead.group(1) + ' ' + obj_b  # "not about X, but Y" → "about Y"
    return obj_b + term


def _neg_fixes(s, bump):
    """Deterministic NEG repair on unprotected prose lines only.
    Every 'not X, but Y' → Y; copula-pairs collapse to the IS-statement.
    Meaning-sensitive NEG (modal, purpose-adverbial edge cases) is DETECTED
    and left to the gate's KB-guided rewrite — never mangled here."""
    n = 0
    out, pos = '', 0
    _CLAUSE_START = ('that', "that's", 'thats', 'it', "it's", 'its', 'he', 'she',
                     'they', 'we', 'you', 'i', 'there', 'this', 'which')
    for m in NEG_DROP.finditer(s):
        if m.start() == 0:
            continue  # sentence-initial "Not X, but Y" — needs a subject; gate handles
        first = m.group(2).strip().lower().split(' ')[0] if m.group(2).strip() else ''
        if first in _CLAUSE_START and len(m.group(2).strip().split(' ')) > 1:
            continue  # "not this, but that's fine" — but-clause is its own
                      # sentence with a subject: new clause, not a complement.
                      # Mechanical drop would garble → gate (KB) handles.
        out += s[pos:m.start()] + _neg_repl(m)
        pos = m.end()
        n += 1
    if n:
        s = out + s[pos:]
        bump('NEG not-X-but-Y dropped', n)
    m = NEG_COPULA.search(s)
    if m:
        # keep the POSITIVE sentence's own verb (preserves "We are", "That's")
        s = s[:m.start()] + f"{m.group(1)}{m.group(4)} {m.group(5)}." + s[m.end():]
        bump('NEG copula collapsed', 1)
    if s.startswith(' ') and not s.lstrip().startswith(' '):
        s = s.lstrip()  # orphan lead-space from opener deletion
    return s


def _match_case(orig, repl):
    """Preserve the casing of a swapped word: LEVERAGE→USE, Leverage→Use."""
    if orig.isupper() and len(orig) > 1:
        return repl.upper()
    if orig[:1].isupper():
        return repl[:1].upper() + repl[1:]
    return repl


def deslop_text(text):
    """Mechanical de-slop on NON-protected regions only. Returns (text, groups).

    Protection is BLOCK-scoped: a marker line ([OWNER VERBATIM], [READ …],
    > DIR:, heading, table row, code fence) and every following line until
    the next blank line is untouchable — quotes and owner words are
    multi-line, so line-prefix protection alone leaks (found by testing)."""
    lines = text.split('\n')
    groups = {}

    def bump(k, n=1):
        groups[k] = groups.get(k, 0) + n

    out = []
    block_protected = False
    for ln in lines:
        low = ln.strip().lower()
        if not ln.strip():  # blank line ends any protected block
            block_protected = False
            out.append(ln)
            continue
        if block_protected or low.startswith(PROTECTED) or any(m in low for m in CONTAINS):
            block_protected = True
            out.append(ln)  # verbatim / citation / direction — untouchable
            continue
        s = ln
        # em/en dashes: ranges keep hyphen, prose dashes become commas
        s2 = EM_DASH_KEEP.sub(r'\1-\2', s)
        dash_n = len(re.findall(r'[–—]', s2))
        if dash_n:
            bump('em/en dashes', dash_n)
            s2 = re.sub(r'\s*[–—]\s*', ', ', s2)
        # word swaps (case-preserving)
        for old, new in WORD_SWAPS:
            pat = re.compile(rf'\b{re.escape(old)}\b', re.I)
            found = pat.findall(s2)
            if found:
                bump('inflated vocabulary', len(found))
                s2 = pat.sub(lambda m: _match_case(m.group(0), new), s2)
        # phrase swaps / deletions
        for pat, repl in PHRASE_SWAPS:
            found = pat.findall(s2)
            if found:
                bump('hype phrases', len(found))
                s2 = pat.sub(repl, s2)
        # filler openers — delete
        for pat in OPENERS:
            found = pat.findall(s2)
            if found:
                bump('filler openers', len(found))
                s2 = pat.sub('', s2)
        # throat-clearing transitions — delete
        found = TRANSITIONS.findall(s2)
        if found:
            bump('throat-clearing transitions', len(found))
            s2 = TRANSITIONS.sub(r'\1', s2)
        # NEG defenses (characters2 port — "not X but Y" / copula collapse)
        s2 = _neg_fixes(s2, bump)
        s2 = re.sub(r'  +', ' ', s2)
        out.append(s2)
    return '\n'.join(out), groups


def assert_protected_unchanged(before, after):
    """Quote-protection invariant: every protected line must be byte-identical."""
    bp = [l for l in before.split('\n') if l.strip().lower().startswith(PROTECTED)]
    ap = [l for l in after.split('\n') if l.strip().lower().startswith(PROTECTED)]
    if bp != ap:
        raise RuntimeError('deslop violated protected lines — abort')


# --- style bank (ported idea: eatusc no-slop POST /api/style + consolidate) -
def style_bank_load(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return []


def style_pairs_block(bank, n=4):
    """Top-N most recent before/after pairs for few-shot rewrite prompts."""
    recent = bank[-n:]
    if not recent:
        return ''
    rows = [f'BEFORE: {p["before"][:300]}\nAFTER:  {p["after"][:300]}' for p in recent]
    return ('\n\nYOUR OWN EDIT HISTORY (match this voice — before/after pairs '
            'you accepted):\n' + '\n---\n'.join(rows))

PUSHING = """You are running the logicvid PUSHING formula on a script chapter.
For each asserted claim in the chapter, produce:
## OBJECTION N — <the strongest question against the claim>
**The claim:** <one line>
**The answer from the banked sources:** <what the attached material actually says — cite file names; if nothing, write SILENT>
**Resolution:** <one line>
**Honest remainder:** <what is still open — one line>
End with: ## VERDICT — what survives, what is contingent, what is open.
No praise, no summary of what's good. Only objections and their honest status."""


def load_pack(slug):
    with open(f'{PACKS_DIR}/{slug}/packs.json' if False else f'{PACKS_DIR}/packs.json') as f:
        manifest = json.load(f)
    pack = next((p for p in manifest['packs'] if p['slug'] == slug), None)
    if not pack:
        raise SystemExit(f'unknown pack: {slug}')
    essay_dir = None
    return pack


def read_pack_file(slug, kind, name):
    return open(f'{PACKS_DIR}/{slug}/{kind}/{name}', encoding='utf-8', errors='replace').read()


def chapters_of(structure_md):
    """Split STRUCTURE.md's tour table into chapter briefs: (label, brief)."""
    chapters = []
    for line in structure_md.splitlines():
        if not line.startswith('|') or line.startswith('|---') or line.startswith('| #'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 3 and cells[0].isdigit():
            chapters.append((cells[1], cells[2]))
    return chapters


def prose_only(text):
    """The text we actually wrote: everything outside protected blocks.
    Gate scores ONLY this — a banked source quote is not AI slop no matter
    how the classifier reads a 1920s translation, and compiler law forbids
    touching it anyway (found by testing: protected quotes tripped the gate)."""
    kept, block_protected = [], False
    for ln in text.split('\n'):
        low = ln.strip().lower()
        if not ln.strip():
            block_protected = False
            continue
        if block_protected or low.startswith(PROTECTED) or any(m in low for m in CONTAINS):
            block_protected = True
            continue
        kept.append(ln)
    return '\n'.join(kept)


def gate(text):
    """Local noslop gate — no API. Scores unprotected prose only.
    Returns (ai_conf, tags). Layered per noslop serving design:
      - <8 words: nothing to gate → pass.
      - classifier.reliable=False (own short-text flag, <~50w): classifier is
        low-evidence → gate on the DETECTOR instead (phrases, not vibes).
      - reliable: calibrated confidence vs SLOP_TARGET."""
    prose = prose_only(text)
    if len(prose.split()) < 8:
        return 0.0, []
    cls = classify(prose)
    det = detect(prose)
    tags = sorted({m['tag'] for m in det.details})
    if not cls.get('reliable', True):
        # short prose: detector patterns decide (any hit → over threshold → one KB rewrite)
        conf = 0.0 if not det.details else 0.3
        return conf, tags
    return round(float(cls['answer']), 4), tags


def run_gate_loop(draft, label, banked_pred=None, bank_path=None):
    """reflow pattern: classify → diagnose → rewrite → re-measure.
    banks prediction first (influence/hloop invariant).
    If bank_path given: every accepted rewrite becomes a before/after pair
    injected into later prompts (style-bank, ported from eatusc no-slop)."""
    history = []
    text = draft
    bank = style_bank_load(bank_path) if bank_path else []
    conf, tags = gate(text)
    history.append({'iter': 0, 'ai_conf': conf, 'tags': tags})
    it = 0
    while conf >= SLOP_TARGET and it < MAX_GATE_ITERS:
        it += 1
        det = detect(prose_only(text))  # only fixable prose — never quote patterns
        lines = [{'tag': m['tag'], 'text': m['text'][:80]} for m in det.details[:20]]
        seen_tags = sorted({m['tag'] for m in det.details})
        # noslop pattern KB: why each pattern reads as machine + how to repair,
        # in the detector's own words (characters2 lesson: classifier = objective,
        # KB guidance = gradient, ad-hoc rule lists lose)
        kb = glossary(seen_tags, 'long') if seen_tags else {}
        repairs_txt = ''
        for tag, k in (kb.get('patterns') or {}).items():
            repairs_txt += f"\n[{tag}] why it reads machine: {k.get('why_slop', '')[:220]}\n"
            for r in (k.get('repairs') or [])[:3]:
                repairs_txt += f"  - {r.get('hint', '')[:160]}\n"
        seq_rules = '\n'.join(f"- {r}" for r in (kb.get('sequencing_rules') or [])[:5])
        prompt = (f"""Revise this script passage to remove AI-slop patterns while preserving meaning, the owner's voice, and every [READ]/[DIR]/[OWNER VERBATIM] marker untouched.

DIAGNOSTIC: {json.dumps(lines, indent=1)[:1800]}
SLOP AI-CONF: {conf} (must fall below {SLOP_TARGET})
{repairs_txt}
REPAIR SEQUENCING (follow in order):{chr(10) + seq_rules if seq_rules else ''}

RULES: keep short/dry/direct; never invent quotes or citations.{style_pairs_block(bank)}

PASSAGE:
{text}""")
        new_text = go_chat(COMPILER, prompt, max_tokens=3000, temperature=0.5)
        # quote-protection invariant: the rewrite must not touch protected lines
        try:
            assert_protected_unchanged(text, new_text)
        except RuntimeError as e:
            print(f'    ! {e} — keeping previous text at iter {it}')
            break
        if bank_path and new_text.strip() and new_text != text:
            bank.append({'before': text[:1200], 'after': new_text[:1200],
                         'label': label, 'at': int(time.time())})
            try:
                json.dump(bank, open(bank_path, 'w'), indent=1)
            except OSError:
                pass
        text = new_text
        conf, tags = gate(text)
        history.append({'iter': it, 'ai_conf': conf, 'tags': tags})
    return text, history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pack', required=True)
    ap.add_argument('--phases', default='enquiry,draft,deslop,push,gate,storyboard')
    ap.add_argument('--chapter', default=None, help='only run this chapter label substring')
    ap.add_argument('--promote', action='store_true', help='overwrite ESSAY.md in essay dir')
    args = ap.parse_args()

    t0 = time.time()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    phases = set(args.phases.split(','))
    pack = load_pack(args.pack)

    # resolve essay dir: from packs manifest we don't have it; map slug→repo
    import glob
    candidates = glob.glob(f'/root/gochema/essays/{args.pack}')
    if not candidates:
        raise SystemExit(f'no essay dir for pack {args.pack} under /root/gochema/essays/')
    essay_dir = candidates[0]
    out_dir = f'{essay_dir}/RUNTIME-{stamp}'
    os.makedirs(out_dir, exist_ok=True)

    report = {'pack': args.pack, 'started': stamp, 'phases': sorted(phases),
              'slop_target': SLOP_TARGET, 'chapters': []}

    # load context
    struct = ''
    for f in ('STRUCTURE.md', 'draft1.md'):
        try:
            struct += f'\n\n## {f}\n' + open(f'{essay_dir}/{f}', encoding='utf-8').read()
        except OSError:
            pass
    ch_briefs = chapters_of(struct)

    # sources for READ grounding (top few pack sources)
    srcs = []
    for name in (pack.get('sources') or [])[:12]:
        try:
            t = read_pack_file(args.pack, 'sources', name)
            if len(t) < 12000:
                srcs.append(f'=== {name} ===\n{t}')
        except OSError:
            pass
    sources_block = '\n\n'.join(srcs)[:60000]

    print(f'[{args.pack}] {len(ch_briefs)} chapters, {len(srcs)} sources loaded → {out_dir}')

    # PHASE: enquiry
    if 'enquiry' in phases:
        print('  [enquiry] building question chain…')
        q = go_chat(COMPILER, f"""From this video STRUCTURE, output the enquiry chain: the questions the film forces, in order, each as one line beginning with "?". Max 12 lines. No commentary.

{struct[:8000]}""", max_tokens=800, temperature=0.3)
        open(f'{out_dir}/ENQUIRY.md', 'w').write('# Enquiry chain\n\n' + q)
        report['enquiry_lines'] = len([l for l in q.splitlines() if l.strip().startswith('?')])
        print(f'    → {report["enquiry_lines"]} questions')

    for label, brief in ch_briefs:
        if args.chapter and args.chapter.lower() not in label.lower():
            continue
        if len(brief) < 40:
            continue
        rec = {'label': label, 'brief': brief[:120]}

        # PHASE: draft (bank prediction first — hloop invariant)
        draft = None
        if 'draft' in phases:
            print(f'  [draft] {label[:50]}…')
            pred_conf, _ = gate(brief)  # prediction banked on the brief itself
            rec['pred_ai_conf'] = pred_conf
            draft = go_chat(COMPILER, f"""Write ONLY this chapter of an essay-film script. Source brief: {brief}

Owner's words (immutable, use [OWNER VERBATIM] where they fit): {struct[:6000]}

Attached sources for READs (verbatim only): 
{sources_block[:30000]}

Format: ## {label} heading, [OWNER VERBATIM]/[READ — cite]/plain bridges/> DIR: as appropriate. 150-350 words.""",
                max_tokens=3500, temperature=0.5)
            open(f'{out_dir}/{label.split("—")[0].strip().replace(" ", "_")}.md', 'w').write(draft)
            rec['draft_words'] = len(draft.split())

        # PHASE: deslop (deterministic — ported MIT no-slop rules; LLM sees only
        # what survives. Protected lines: [OWNER VERBATIM]/[READ]/DIR/heads.)
        if 'deslop' in phases and draft:
            print(f'  [deslop] {label[:50]}…')
            cleaned, groups = deslop_text(draft)
            assert_protected_unchanged(draft, cleaned)  # quotes untouchable
            rec['deslop'] = groups
            if cleaned != draft:
                open(f'{out_dir}/{label.split("—")[0].strip().replace(" ", "_")}-deslopped.md', 'w').write(cleaned)
                print(f'    → {sum(groups.values())} mechanical fixes: {groups}')
                draft = cleaned
            else:
                print('    → no mechanical slop found')

        # PHASE: push
        if 'push' in phases and draft:
            print(f'  [push] {label[:50]}…')
            push = go_chat(PUSHING, f'CHAPTER:\n{draft}\n\nSOURCES:\n{sources_block[:20000]}',
                           max_tokens=2500, temperature=0.4)
            open(f'{out_dir}/{label.split("—")[0].strip().replace(" ", "_")}-PUSH.md', 'w').write(push)
            rec['push_objections'] = len(re.findall(r'^## OBJECTION', push, re.M))

        # PHASE: gate (slop loop — LLM rewrites only for what deslop couldn't fix)
        if 'gate' in phases and draft:
            print(f'  [gate] {label[:50]}…')
            bank_path = f'{out_dir}/STYLE-BANK.json'
            gated, hist = run_gate_loop(draft, label, rec.get('pred_ai_conf'), bank_path)
            rec['gate'] = hist
            rec['gate_pass'] = hist[-1]['ai_conf'] < SLOP_TARGET
            if gated != draft:
                open(f'{out_dir}/{label.split("—")[0].strip().replace(" ", "_")}-gated.md', 'w').write(gated)
                draft = gated
            print(f'    → final AI-conf {hist[-1]["ai_conf"]} (target < {SLOP_TARGET}) {"PASS" if rec["gate_pass"] else "FAIL"}')

        report['chapters'].append(rec)

    # PHASE: storyboard
    if 'storyboard' in phases:
        print('  [storyboard] generating shot rows…')
        essay_files = sorted(glob.glob(f'{out_dir}/*-gated.md')) or sorted(glob.glob(f'{out_dir}/*.md'))
        rows = ['| # | t0–t1 | Visual | Audio | Overlay data | Dur |',
                '|---|---|---|---|---|---|']
        t = 0
        n = 0
        for f in essay_files:
            if 'PUSH' in f or 'ENQUIRY' in f:
                continue
            text = open(f).read()
            dirs = re.findall(r'> DIR:\s*(.+)', text)
            heading = (re.search(r'^##\s+(.+)', text, re.M) or [None, os.path.basename(f)])[1]
            dur = max(20, min(120, len(text.split()) // 2))  # ~2 wps + dir overhead
            n += 1
            m0, m1 = t // 60, t % 60
            t2 = t + dur
            visual = dirs[0] if dirs else heading[:60]
            audio = 'owner voice + [READ]s' if '[READ' in text else 'owner voice'
            rows.append(f'| S{n:02d} | {m0}:{m1:02d}–{t2 // 60}:{t2 % 60:02d} | {visual[:70]} | {audio} | {"READ card" if "[READ" in text else "—"} | {dur}s |')
            t = t2
        rows.append(f'\nTotal: ~{t // 60}:{t % 60:02d} across {n} shots')
        open(f'{out_dir}/STORYBOARD.md', 'w').write(f'# STORYBOARD — {args.pack} (runtime-generated)\n\n' + '\n'.join(rows))
        print(f'    → {n} shots, ~{t // 60}:{t % 60:02d}')

    report['finished'] = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    report['elapsed_s'] = round(time.time() - t0, 1)
    with open(f'{out_dir}/report.json', 'w') as f:
        json.dump(report, f, indent=1)
    print(f'\nDone in {report["elapsed_s"]}s → {out_dir}')
    print(json.dumps({k: v for k, v in report.items() if k != 'chapters'}, indent=1))


if __name__ == '__main__':
    main()
