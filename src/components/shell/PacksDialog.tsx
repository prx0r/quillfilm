import { useEffect, useState } from 'react';
import { fetchPackManifest, type PackDef } from '../../services/packs';

/** File → Video packs… Lists one-click film packs (manuscript + evidence bank).
 * Lives outside the reachability-guarded panels: new file, own test ids. */
export function PacksDialog({ open, onClose, onLoad, loadingSlug }: {
  open: boolean;
  onClose: () => void;
  onLoad: (slug: string, title: string) => void;
  loadingSlug: string | null;
}) {
  const [packs, setPacks] = useState<PackDef[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError(null);
    setPacks(null);
    fetchPackManifest()
      .then(m => { if (!cancelled) setPacks(m.packs); })
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, [open ]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)' }} onClick={onClose} data-testid="packs-dialog">
      <div className="rounded-xl p-6 w-[min(92vw,480px)] max-h-[80vh] overflow-auto" style={{ background: '#111116', border: '1px solid #2a2a33' }} onClick={e => e.stopPropagation()}>
        <div className="flex items-start justify-between mb-1">
          <h2 className="text-lg font-semibold" style={{ color: '#f3f1ec' }}>Video packs</h2>
          <button onClick={onClose} data-testid="packs-close" aria-label="Close video packs" style={{ color: '#8d8b93' }}>✕</button>
        </div>
        <p className="text-sm mb-4" style={{ color: '#8d8b93' }}>One film per pack: manuscript straight into the editor, evidence bank into the Cite library. Attach 1–3 sources in chat to write against them.</p>
        {error && <p className="text-sm mb-2" data-testid="packs-error" style={{ color: '#E8102E' }}>Couldn’t load packs: {error}</p>}
        {!error && packs === null && <p className="text-sm" style={{ color: '#8d8b93' }}>Loading packs…</p>}
        {packs && packs.length === 0 && <p className="text-sm" style={{ color: '#8d8b93' }}>No packs published yet.</p>}
        {packs?.map(p => (
          <div key={p.slug} className="rounded-lg p-4 mb-3" style={{ background: '#1a1a21', border: '1px solid #2a2a33' }}>
            <div className="font-medium mb-1" style={{ color: '#f3f1ec' }}>{p.title}</div>
            {p.blurb && <div className="text-sm mb-3" style={{ color: '#8d8b93' }}>{p.blurb}</div>}
            <button
              onClick={() => onLoad(p.slug, p.title)}
              disabled={loadingSlug !== null}
              data-testid={`pack-load-${p.slug}`}
              className="px-4 py-2 rounded-lg text-sm font-semibold"
              style={{ background: '#F5C76B', color: '#111' }}
            >
              {loadingSlug === p.slug ? 'Loading…' : `Load ${p.manuscripts[0]?.title ?? 'pack'} + ${p.sources.length} sources`}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
