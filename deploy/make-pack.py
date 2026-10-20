#!/usr/bin/env python3
"""Build a quill pack from a gochema essay directory.

Usage: make-pack.py <slug> <essay-dir>   (e.g. make-pack.py rebirth /root/gochema/essays/rebirth-explained)

Output: /root/manuscriptAI/public/packs/<slug>/
  - manuscripts/*.docx  (ESSAY, STORYBOARD, draft1 — whichever exist; import into editor)
  - sources/WEAVE.md + sources/resources-*.md (upload to Cite library, attach in chat)
  - sources/quotes-*.txt (ATI chrome stripped; attach when verifying a long passage)
  - PACK-README.md (load order + what-to-attach-when)

Repeatable for every video idea: one slug per film.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

QUILL = Path('/root/manuscriptAI/public/packs')

TAIL_MARKERS = [
    'How to cite this document',
    'Access to Insight is owned',
    'Alternate format',
    'Help | Site map',
    'Terms of use',
]


def strip_ati_chrome(text: str) -> str:
    """ATI dumps wrap the sutta in ~100 lines of metadata/nav + footer.
    Keep the body: from the first long prose line to the first footer marker."""
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    lines = text.splitlines()
    start = 0
    # Anchor on the sutta's opening formula; fall back to first long prose line.
    opens = [r'I have heard that on one occasion', r'Thus have I heard',
             r'Dwelling at', r'On one occasion']
    for i, ln in enumerate(lines):
        if any(re.search(p, ln) for p in opens):
            start = i
            break
    else:
        for i, ln in enumerate(lines):
            s = ln.strip()
            if len(s) > 150 and not s.startswith(
                    ('{', '[', '}', 'http', 'Format', 'Path', 'Tipitaka',
                     'Creative Commons', 'Documents linked', 'Transcribed',
                     'Copyright', '©')):
                start = i
                break
    end = len(lines)
    for i in range(start, len(lines)):
        if any(m in lines[i] for m in TAIL_MARKERS):
            end = i
            break
    body = '\n'.join(lines[start:end])
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    return body


MANUSCRIPT_CANDIDATES = ['ESSAY.md', 'STORYBOARD.md', 'MOVIE.md', 'draft1.md',
                           'STRUCTURE.md', 'SPEC.md', 'SOURCE.md', 'VIDEO.md',
                           'PUSHBACK.md']


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('slug', nargs='?')
    ap.add_argument('essay_dir', nargs='?')
    ap.add_argument('--title', default='')
    ap.add_argument('--blurb', default='')
    ap.add_argument('--manifest-only', action='store_true',
                    help='only regenerate packs.json from existing pack dirs')
    a = ap.parse_args()
    if a.manifest_only:
        write_manifest(None, None, '', '')
        print('manifest regenerated')
        return
    slug, essay = a.slug, Path(a.essay_dir)
    if not essay.is_dir():
        raise SystemExit(f'essay dir does not exist: {essay}')
    title = a.title or slug.replace('-', ' ').title()
    out = QUILL / slug
    man, src = out / 'manuscripts', out / 'sources'
    if out.exists():
        shutil.rmtree(out)
    man.mkdir(parents=True)
    src.mkdir(parents=True)

    made = []
    for name in MANUSCRIPT_CANDIDATES:
        f = essay / name
        if f.exists():
            docx = man / (f.stem + '.docx')
            subprocess.run(
                ['pandoc', str(f), '-o', str(docx),
                 '--metadata', f'title={slug} — {f.stem}'],
                check=True)
            made.append(docx.name)

    copied = []
    for pat in ['WEAVE.md', 'WEAVE-GLOBAL.md', 'ONTOLOGY.md', 'TAKES.md',
                 'MOTHER-OBJECTIONS.md', 'JOURNEY.md', 'ACQUIRE.md']:
        f = essay / pat
        if f.exists():
            shutil.copy(f, src / f.name)
            copied.append(f.name)
    for res in sorted((essay / 'resources').glob('*.md')) if (essay / 'resources').exists() else []:
        shutil.copy(res, src / f'resources-{res.name}')
        copied.append(f'resources-{res.name}')
    quotes = essay / 'quotes'
    if quotes.exists():
        for q in sorted(quotes.glob('*.txt')):
            text = q.read_text(encoding='utf-8', errors='replace')
            cleaned = strip_ati_chrome(text) if len(text) > 30000 else text
            (src / f'quotes-{q.name}').write_text(cleaned, encoding='utf-8')
            copied.append(f'quotes-{q.name} (cleaned)' if len(text) > 30000 else f'quotes-{q.name}')
    args = essay / 'arguments'
    if args.exists():
        for aj in sorted(args.glob('*.json')):
            try:
                json.loads(aj.read_text(encoding='utf-8'))
            except Exception as e:
                print(f'  SKIP {aj.name}: not valid JSON ({e})')
                continue
            shutil.copy(aj, src / f'arguments-{aj.name}')
            copied.append(f'arguments-{aj.name}')
    for t in sorted(essay.glob('*.txt')):
        shutil.copy(t, src / f'text-{t.name}')
        copied.append(f'text-{t.name}')

    # Raw .md manuscripts ride along for one-click loading (File → Video
    # packs… fetches these straight into the editor — no import dialog).
    md_made = []
    for name in MANUSCRIPT_CANDIDATES:
        f = essay / name
        if f.exists():
            shutil.copy(f, man / f.name)
            md_made.append(f.name)

    (out / 'PACK-README.md').write_text(
        f"""# {title} — quill pack
Manuscripts (File → Video packs… loads these straight into the editor;
the .docx files are for manual import): {', '.join(md_made) or 'none'}
Sources (auto-loaded with the pack; also uploadable by hand to the Cite
library): {len(copied)} files — WEAVE quote bank, resources per school,
sutta extracts.

## How the AI helps (already wired)
- **Chat panel → attach 1–3 sources** to any chat message. The compiler prompt
  is baked in: it checks quotes verbatim, flags SILENT claims, never
  rewrites your voice. Keep attachments tight (WEAVE + the school file).
- **Analyze All** runs the critic agents over the manuscript itself.
- **Highlight any sentence → Verify** cross-checks it against loaded sources.

## Rule
One film = one manuscript + its pack sources attached. Don't attach the
whole library — the AI's context is shared across attachments, so 1–3 files
per question keeps quotes exact.
""")

    write_manifest(slug, title, a.blurb, out)

    print(f'pack {slug}: {len(made)} docx + {len(md_made)} md, {len(copied)} sources -> {out}')


def write_manifest(slug, title, blurb, out):
    # Packs manifest (File → Video packs… reads this; rebuilt every run so
    # new packs appear without touching app code). Preserves titles/blurbs
    # so post-copy shared files and re-runs never wipe metadata.
    import json
    mf = {'packs': []}
    if (QUILL / 'packs.json').exists():
        try:
            mf = json.loads((QUILL / 'packs.json').read_text())
        except Exception:
            pass
    old_by_slug = {p['slug']: p for p in mf.get('packs', [])}
    packs = []
    for d in sorted(QUILL.iterdir()):
        if not d.is_dir():
            continue
        old = old_by_slug.get(d.name, {})
        mans = [{'file': f.name, 'title': f.stem} for f in sorted((d / 'manuscripts').glob('*.md'))] if (d / 'manuscripts').exists() else []
        srcs = sorted(f.name for f in (d / 'sources').iterdir() if f.is_file()) if (d / 'sources').exists() else []
        packs.append({
            'slug': d.name,
            'title': old.get('title') or (title if d.name == slug else '') or d.name.replace('-', ' ').title(),
            'blurb': old.get('blurb') or '',
            'manuscripts': mans,
            'sources': srcs,
        })
    if slug and blurb:
        for p in packs:
            if p['slug'] == slug:
                p['title'] = title
                p['blurb'] = blurb
    (QUILL / 'packs.json').write_text(json.dumps({'packs': packs}, indent=1))


if __name__ == '__main__':
    main()
