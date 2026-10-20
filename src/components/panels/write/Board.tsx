import { useState } from 'react';
import { boardToJson, boardToMarkdown, useBoardStore } from '../../../stores/useBoardStore';

/** Storyboard section: shot rows from the loaded pack with per-shot status.
 * Statuses persist locally; Copy board exports markdown + JSON for the
 * render pipeline and the JOURNEY.md seed. Lives outside the guarded files;
 * reached by the board rows in reachability.test.tsx. */
export function Board() {
  const { packTitle, rows, journey, advance } = useBoardStore();
  const [copied, setCopied] = useState<string | null>(null);

  const copy = async (kind: 'board' | 'journey') => {
    const b = useBoardStore.getState();
    const text = kind === 'board'
      ? boardToMarkdown(b) + '\n\n```json\n' + boardToJson(b) + '\n```\n'
      : `# Journey log — ${b.packTitle || 'untitled'}\n\n${b.journey.map(j => `- ${j}`).join('\n') || '(no entries yet)'}\n`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(kind);
      setTimeout(() => setCopied(null), 2000);
    } catch { /* clipboard unavailable in this context */ }
  };

  if (rows.length === 0) {
    return (
      <p className="text-[13px]" style={{ color: 'var(--text-muted)' }}>
        No board yet. Load a video pack (File → Video packs…) and its
        storyboard rows appear here with per-shot status.
      </p>
    );
  }

  let lastAct = '';
  return (
    <div>
      <div className="text-[13px] mb-2 font-semibold" style={{ color: 'var(--text-primary)' }} data-testid="board-pack">
        {packTitle} · {rows.filter(r => r.status === 'done').length}/{rows.length} done
      </div>
      <div className="space-y-1 max-h-96 overflow-auto">
        {rows.map(r => {
          const head = r.act && r.act !== lastAct ? ((lastAct = r.act), (
            <div key={`act-${r.id}`} className="text-[11px] font-bold uppercase tracking-wider pt-2" style={{ color: 'var(--text-muted)' }}>
              {r.act}
            </div>
          )) : null;
          return (
            <div key={r.id}>
              {head}
              <div className="flex items-center gap-2 py-1" data-testid={`board-row-${r.id}`}>
                <span className="text-[12px] font-mono w-10 shrink-0" style={{ color: 'var(--text-muted)' }}>
                  {r.status === 'done' ? '✓' : r.status === 'locked' ? '~' : '○'} {r.id}
                </span>
                <span className="text-[12px] flex-1 truncate" style={{ color: 'var(--text-primary)' }} title={r.visual}>
                  {r.time ? `${r.time} — ` : ''}{r.visual || r.audio || '(no description)'}
                </span>
                <button
                  data-testid="control-board-advance"
                  onClick={() => advance(r.id)}
                  disabled={r.status === 'done'}
                  className="text-[11px] px-2 py-0.5 rounded-md border shrink-0"
                  style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}
                >
                  Advance
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex gap-2 mt-2">
        <button data-testid="control-board-copy" onClick={() => void copy('board')} className="text-[11px] px-2 py-1 rounded-md border" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>
          {copied === 'board' ? 'Copied' : 'Copy board'}
        </button>
        <button data-testid="control-board-journey" onClick={() => void copy('journey')} className="text-[11px] px-2 py-1 rounded-md border" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>
          {copied === 'journey' ? 'Copied' : 'Copy journey log'}
        </button>
      </div>
      {journey.length > 0 && (
        <div className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
          Last: {journey[journey.length - 1]}
        </div>
      )}
    </div>
  );
}
