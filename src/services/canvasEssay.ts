/** Place a pack's essay onto the sketch canvas as chapter objects.
 * Shared by the WriteCanvas "load essay" button and the ?canvas=<slug>
 * boot path. Idempotent: won't stack a second copy of the same essay. */

import { useCanvasStore, type CanvasBlock } from '../stores/useCanvasStore';
import { useBoardStore } from '../stores/useBoardStore';

export interface ImportResult {
  slug: string;
  chapters: number;
  existing?: boolean;
}

export async function importEssayToCanvas(preferredSlug?: string): Promise<ImportResult> {
  const st = useCanvasStore.getState();
  let slug = preferredSlug || st.packSlug || useBoardStore.getState().packSlug;
  let mans: Array<{ file: string }> = [];
  const m = await (await fetch('/packs/packs.json')).json();
  const packs: Array<{ slug: string; manuscripts: Array<{ file: string }> }> = m.packs ?? [];

  if (slug) {
    mans = packs.find(p => p.slug === slug)?.manuscripts ?? [];
  }
  if (!mans.length) {
    const p = packs.find(x => (x.manuscripts ?? []).some(y => y.file === 'ESSAY.md'))
      ?? packs.find(x => (x.manuscripts ?? []).length);
    if (!p) return { slug: '', chapters: 0 };
    slug = p.slug;
    mans = p.manuscripts ?? [];
  }
  const doc = mans.find(x => x.file === 'ESSAY.md') ?? mans[0];
  if (!doc) return { slug, chapters: 0 };
  const md = await (await fetch(`/packs/${slug}/manuscripts/${encodeURIComponent(doc.file)}`)).text();

  // split: chapter-level if the file has ## headings, else blank-line blocks
  const parts = md.split(/\n(?=##\s)/).map(s => s.trim()).filter(Boolean);
  const chunks = parts.length > 1 ? parts : md.split(/\n{2,}/).map(s => s.trim()).filter(Boolean);
  if (!chunks.length) return { slug, chapters: 0 };

  // idempotent: first chunk's opening already on canvas → nothing to add
  const probe = chunks[0].slice(0, 80);
  if (useCanvasStore.getState().blocks.some(b => b.text.includes(probe))) {
    return { slug, chapters: 0, existing: true };
  }

  let y = 60;
  for (let i = 0; i < chunks.length; i++) {
    const chunk = chunks[i].slice(0, 6000);
    const h = Math.max(60, Math.min(420, 30 + chunk.split('\n').join('').length / 4.8));
    useCanvasStore.getState().addBlock(i === 0 ? 80 : 120 + (i % 2) * 26, y);
    y += h + 18;
    const id = useCanvasStore.getState().blocks[useCanvasStore.getState().blocks.length - 1]?.id;
    if (id) useCanvasStore.getState().updateText(id, chunk);
  }
  useCanvasStore.getState().setPack(slug);
  return { slug, chapters: chunks.length };
}
