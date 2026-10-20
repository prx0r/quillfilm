/** Canvas pull: on writing pause, ask the model for TYPED CARDS only.
 * Opencanvas lesson: "The model never prints the answer" — it returns
 * typed payloads the canvas renders. Cards are evidence-bound (attached
 * pack sources are the only allowed material — same law as chat). */

export type CardKind = 'quote' | 'source' | 'objection' | 'next';

export interface CanvasCard {
  k: CardKind;
  t: string;
  src?: string;
}

const PACKS_RANK = (n: string): number => {
  const l = n.toLowerCase();
  if (l.startsWith('weave')) return 0;
  if (/^(takes|mother-objections|journey|pushback|acquire)/.test(l)) return 1;
  if (l.startsWith('resources-')) return 2;
  if (l.startsWith('quotes-')) return 3;
  return 9;
};

const SYSTEM = `You are a silent drafting copilot on an infinite writing canvas.
The user is writing a script; you attach FOUNDED cards beside their words.
Return ONLY a JSON array (no prose, no fences), max 3 items:
[{"k":"quote"|"source"|"objection"|"next","t":"<=28 words","src":"file or WEAVE id"}]
- quote: a verbatim line from an attached source (src = file name)
- source: which attached file covers this passage (src = file name)
- objection: the strongest counter a critic would raise
- next: one open question this writing implies (the enquiry chain)
Every card must be grounded in the attached sources or in the passage itself.
If nothing earns a card, return [].`;

const KINDS: CardKind[] = ['quote', 'source', 'objection', 'next'];

export function parseCards(raw: string): CanvasCard[] {
  // tolerate fences/prose: first [...] or {...→[...]}
  const m = raw.match(/\[[\s\S]*\]/);
  if (!m) return [];
  try {
    const arr = JSON.parse(m[0]);
    if (!Array.isArray(arr)) return [];
    return arr
      .filter(o => o && typeof o === 'object' && KINDS.includes(o.k) && typeof o.t === 'string' && o.t.trim())
      .slice(0, 4)
      .map(o => ({ k: o.k, t: o.t.trim().slice(0, 240), src: typeof o.src === 'string' ? o.src.slice(0, 80) : undefined }));
  } catch {
    return [];
  }
}

/** Fetch 2 whole pack sources (quote-safe) for grounding one pull. */
async function pullSources(packSlug?: string): Promise<string> {
  try {
    const m = await (await fetch('/packs/packs.json')).json();
    const flat: Array<{ slug: string; file: string }> = [];
    for (const p of m.packs ?? []) for (const s of p.sources ?? []) flat.push({ slug: p.slug, file: s });
    // current pack first, then global rank (its WEAVE wins over other packs')
    flat.sort((a, b) =>
      (Number(packSlug !== undefined && b.slug === packSlug) - Number(packSlug !== undefined && a.slug === packSlug))
      || PACKS_RANK(a.file) - PACKS_RANK(b.file));
    let total = '';
    for (const p of flat.slice(0, 2)) {
      try {
        const r = await fetch(`/packs/${p.slug}/sources/${encodeURIComponent(p.file)}`);
        if (r.ok) total += `\n=== ${p.file} ===\n${(await r.text()).slice(0, 14000)}`;
      } catch { /* grounding is best-effort */ }
    }
    return total.trim();
  } catch {
    return '';
  }
}

/** One pause-pull. Returns [] on any failure — a quiet canvas beats an error. */
export async function pullCards(blockText: string, packSlug?: string, signal?: AbortSignal): Promise<CanvasCard[]> {
  const text = blockText.replace(/\s+/g, ' ').trim().slice(0, 1500);
  if (text.length < 40) return [];
  let sources = '';
  try {
    sources = await pullSources(packSlug);
  } catch { /* proceed ungrounded — cards get low quota */ }
  const body = JSON.stringify({
    model: 'longcat-2.5-preview-free',
    messages: [
      { role: 'system', content: SYSTEM },
      { role: 'user', content: `Attached sources:${sources || ' (none — only use the passage)'}\n\nPassage:\n"""\n${text}\n"""\n\nJSON array only:` },
    ],
    temperature: 0.3,
    max_tokens: 600,
    enable_thinking: false, think: false,
    chat_template_kwargs: { enable_thinking: false },
  });
  const res = await fetch('/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal,
  });
  if (!res.ok) return [];
  const data = await res.json();
  const content = data?.choices?.[0]?.message?.content;
  if (typeof content !== 'string') return [];
  return parseCards(content);
}

export const PAUSE_MS = 2600;
