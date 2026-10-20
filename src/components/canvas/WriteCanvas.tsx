import { useCallback, useEffect, useRef, useState } from 'react';
import { PAUSE_MS, pullCards, type CardKind } from '../../services/canvasPull';
import { useCanvasStore, type CanvasBlock } from '../../stores/useCanvasStore';
import { useBoardStore } from '../../stores/useBoardStore';
import { importEssayToCanvas } from '../../services/canvasEssay';

const CARD_STYLE: Record<CardKind, { label: string; color: string; bg: string }> = {
  quote:    { label: '❝',  color: '#F5C76B', bg: 'rgba(245,199,107,.10)' },
  source:   { label: '§',   color: '#5EC4B6', bg: 'rgba(94,196,182,.10)' },
  objection:{ label: '⚡',  color: '#E8102E', bg: 'rgba(232,16,46,.10)' },
  next:     { label: '→',   color: '#8B5CF6', bg: 'rgba(139,92,246,.10)' },
};

/** One text block: free type, pause-pull cards, ▷ render (TTS scene). */
function Block({ b, zoom }: { b: CanvasBlock; zoom: number }) {
  const { updateText, setCards, setPulling, markPulled, removeBlock, selected, toggleSelect, applyPositions } = useCanvasStore();
  const ref = useRef<HTMLDivElement>(null);
  const timer = useRef<number | null>(null);
  const abort = useRef<AbortController | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [rendering, setRendering] = useState(false);
  const isSelected = selected.includes(b.id);

  /** Drag the block (or the whole shift-selected set) as one object —
   * world coords, so zoom doesn't skew the delta. One persist on drop. */
  const startDrag = (e: React.PointerEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const st = useCanvasStore.getState();
    const ids = st.selected.includes(b.id) ? st.selected : [b.id];
    const origs = ids
      .map(id => st.blocks.find(x => x.id === id))
      .filter((x): x is CanvasBlock => !!x)
      .map(x => ({ id: x.id, x: x.x, y: x.y }));
    const sx = e.clientX, sy = e.clientY;
    let last: Array<{ id: string; x: number; y: number }> = origs;
    const onMove = (ev: PointerEvent) => {
      const dx = (ev.clientX - sx) / zoom;
      const dy = (ev.clientY - sy) / zoom;
      last = origs.map(o => ({ id: o.id, x: o.x + dx, y: o.y + dy }));
      useCanvasStore.getState().applyPositions(last, false);
    };
    const onUp = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      useCanvasStore.getState().applyPositions(last, true);
    };
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp, { once: true });
  };

  const doPull = useCallback(async (text: string) => {
    if (!text || text.trim().length < 40) return;
    abort.current?.abort();
    const ac = new AbortController();
    abort.current = ac;
    setPulling(b.id, true);
    markPulled(b.id);
    try {
      const cards = await pullCards(text, useCanvasStore.getState().packSlug, ac.signal);
      if (!ac.signal.aborted) setCards(b.id, cards);
    } catch { setCards(b.id, []); }
  }, [b.id, setCards, setPulling, markPulled]);

  /** v1 render: TTS the block + a scene flash. The visual engine (hyperframes)
   * plugs into this same button next. */
  const doRender = useCallback(async () => {
    const text = (ref.current?.textContent ?? '').trim();
    if (text.length < 20 || rendering) return;
    setRendering(true);
    try {
      const res = await fetch('/api/tts/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.slice(0, 3500), label: 'sketch', engine: 'phonon' }),
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        alert(`render failed: ${(e as { error?: string }).error || res.status}`);
        return;
      }
      const { id, ext } = await res.json();
      const el = ref.current;
      el?.classList.add('scene-playing');
      const a = new Audio(`/api/tts/${id}.${ext || 'mp3'}`);
      a.onended = () => el?.classList.remove('scene-playing');
      await a.play().catch(() => el?.classList.remove('scene-playing'));
    } catch (e) {
      alert(`render failed: ${e instanceof Error ? e.message : e}`);
    } finally {
      setRendering(false);
    }
  }, [rendering]);

  const onInput = () => {
    const text = ref.current?.textContent ?? '';
    updateText(b.id, text);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void doPull(text), PAUSE_MS);
  };

  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); abort.current?.abort(); }, []);

  return (
    <div
      className="absolute group"
      style={{
        left: b.x, top: b.y, width: 620, maxWidth: '52vw',
        outline: isSelected ? '2px solid #F5C76B' : 'none',
        outlineOffset: 3,
        borderRadius: 8,
      }}
    >
      <button
        data-testid={`block-handle-${b.id}`}
        onPointerDown={startDrag}
        title="Drag to move · shift-click blocks first to move several"
        className="absolute -top-3 -right-2 z-10 px-1 text-[13px] rounded cursor-grab active:cursor-grabbing select-none opacity-40 hover:opacity-100"
        style={{ color: '#F5C76B', background: 'var(--surface-0, #07070a)', border: '1px solid var(--border)' }}
      >
        ⠿
      </button>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        data-testid={`canvas-block-${b.id}`}
        onInput={onInput}
        onPointerDown={(e) => { if (e.shiftKey) { e.preventDefault(); toggleSelect(b.id, true); } }}
        onKeyDown={(e) => { if (e.key === 'Backspace' && !(ref.current?.textContent ?? '').trim()) { e.preventDefault(); removeBlock(b.id); } }}
        className="outline-none px-3 py-2 rounded-lg text-[17px] leading-relaxed"
        style={{
          fontFamily: 'Crimson Pro, Georgia, serif',
          color: 'var(--text-primary, #f3f1ec)',
          minHeight: 44, whiteSpace: 'pre-wrap',
          transition: 'box-shadow .4s', boxShadow: '0 0 0 rgba(245,199,107,0)',
        }}
        role="textbox"
      />
      <style>{`.scene-playing{box-shadow:0 0 0 2px #F5C76B, 0 0 42px rgba(245,199,107,.35) !important}`}</style>
      <div className="flex flex-wrap gap-1.5 mt-1 items-center">
        {b.text.trim().length >= 20 && (
          <button
            data-testid="sketch-render"
            onClick={() => void doRender()}
            disabled={rendering}
            className="text-[11px] px-2 py-1 rounded-md border"
            style={{ color: '#F5C76B', borderColor: '#F5C76B66', opacity: rendering ? 0.5 : 1 }}
            title="Render this block: TTS voice + scene flash (visual engine plugs in next)"
          >
            {rendering ? 'rendering…' : '▷ render'}
          </button>
        )}
        {b.pulling && <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>pulling…</span>}
        {b.cards.map((c, i) => {
          const st = CARD_STYLE[c.k];
          const key = `${b.id}-c${i}`;
          const isOpen = expanded === key;
          return (
            <span
              key={key}
              data-testid="canvas-card"
              onClick={() => setExpanded(isOpen ? null : key)}
              className="cursor-pointer text-[12px] px-2 py-1 rounded-md border inline-block"
              style={{ color: st.color, background: st.bg, borderColor: `${st.color}55`, maxWidth: 420 }}
              title={c.src ? `source: ${c.src}` : c.k}
            >
              {st.label} {isOpen ? c.t : (c.t.length > 64 ? c.t.slice(0, 64) + '…' : c.t)}
              {c.src && <span className="text-[10px] font-mono opacity-60"> [{c.src}]</span>}
            </span>
          );
        })}
        {b.text.trim().length >= 40 && !b.cards.length && !b.pulling && (
          <button
            data-testid="canvas-pull"
            onClick={() => void doPull(b.text)}
            className="text-[11px] px-2 py-1 rounded-md border"
            style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}
          >
            ◇ pull cards
          </button>
        )}
        <span className="text-[9px] font-mono" style={{ color: 'var(--text-muted)', opacity: zoom < 0.7 ? 0 : 1 }}>
          {Math.round(b.x)},{Math.round(b.y)}
        </span>
      </div>
    </div>
  );
}

/** THE BLANK CANVAS — fluid zoom/pan, click-to-write, essay import, block render.
 * Endgame v1 per owner: "full essay on the blank canvas that i can then edit
 * and fluidly zoom in and out of to make edits, then click render". */
export function WriteCanvas({ onClose }: { onClose: () => void }) {
  const { blocks, addBlock, clearAll, packSlug, setPack } = useCanvasStore();
  const boardPack = useBoardStore(s => s.packSlug);
  const surfaceRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<HTMLDivElement>(null);
  const [view, setView] = useState({ tx: 0, ty: 0, k: 1 });
  const dragRef = useRef<{ sx: number; sy: number; tx: number; ty: number; pan: boolean } | null>(null);
  const [importing, setImporting] = useState(false);
  const [status, setStatus] = useState('');
  const selCount = useCanvasStore(s => s.selected.length);

  // Esc clears the selection set
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') useCanvasStore.getState().clearSelection();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => { if (boardPack) setPack(boardPack); }, [boardPack, setPack]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const el = surfaceRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const cx = e.clientX - r.left, cy = e.clientY - r.top;
    setView(v => {
      const k2 = Math.min(3, Math.max(0.25, v.k * (e.deltaY > 0 ? 0.9 : 1.11)));
      const scale = k2 / v.k;
      return { k: k2, tx: cx - (cx - v.tx) * scale, ty: cy - (cy - v.ty) * scale };
    });
  };

  /** shift+drag / middle-drag = pan; plain click on empty = new block in world coords. */
  const onPointerDown = (e: React.PointerEvent) => {
    if (e.target !== surfaceRef.current) return;
    if (e.shiftKey || e.button === 1) {
      dragRef.current = { sx: e.clientX, sy: e.clientY, tx: view.tx, ty: view.ty, pan: true };
      (e.target as Element).setPointerCapture?.(e.pointerId);
      return;
    }
    useCanvasStore.getState().clearSelection();
    const r = surfaceRef.current!.getBoundingClientRect();
    const wx = (e.clientX - r.left - view.tx) / view.k;
    const wy = (e.clientY - r.top - view.ty) / view.k;
    addBlock(Math.max(0, wx - 8), Math.max(0, wy - 12));
    setTimeout(() => {
      const nodes = viewRef.current?.querySelectorAll<HTMLElement>('[data-testid^="canvas-block-"]');
      nodes[nodes.length - 1]?.focus();
    }, 30);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragRef.current?.pan) return;
    const d = dragRef.current;
    setView(v => ({ ...v, tx: d.tx + (e.clientX - d.sx), ty: d.ty + (e.clientY - d.sy) }));
  };
  const onPointerUp = () => { dragRef.current = null; };

  const zoomBy = (f: number) => setView(v => {
    const el = surfaceRef.current;
    const r = el?.getBoundingClientRect();
    const cx = r ? r.width / 2 : 0, cy = r ? r.height / 2 : 0;
    const k2 = Math.min(3, Math.max(0.25, v.k * f));
    const s = k2 / v.k;
    return { k: k2, tx: cx - (cx - v.tx) * s, ty: cy - (cy - v.ty) * s };
  });

  /** Import the current pack's essay: chapters become stacked blocks. */
  const loadEssay = async () => {
    if (importing) return;
    setImporting(true);
    setStatus('loading essay…');
    try {
      const r = await importEssayToCanvas(packSlug || boardPack);
      if (!r.chapters) {
        setStatus(r.existing ? 'essay already on canvas' : 'no manuscript in pack');
      } else {
        setPack(r.slug);
        setStatus(`${r.chapters} chapters placed — ⠿ drag to arrange · wheel zooms · click to edit`);
      }
      setTimeout(() => setStatus(''), 7000);
    } catch (e) {
      setStatus(`import failed: ${e instanceof Error ? e.message : e}`);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex flex-col" style={{ background: 'var(--surface-0, #07070a)' }} data-testid="canvas-mode">
      <div className="flex items-center gap-3 px-4 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="text-[13px] font-semibold tracking-wide" style={{ color: 'var(--text-primary)' }}>SKETCH</span>
        <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          {status || (selCount > 0
            ? `${selCount} selected — drag ⠿ to move together · Esc clears`
            : (packSlug ? `grounded by ${packSlug} · click to write · ⠿ drags · shift-click selects · shift+drag pans · wheel zooms` : 'click anywhere · write · shift-click selects · ⠿ drags · pause → cards'))}
        </span>
        <span className="flex-1" />
        <button data-testid="sketch-load" onClick={() => void loadEssay()} disabled={importing}
          className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: '#F5C76B66', color: '#F5C76B' }}>
          {importing ? 'importing…' : 'load essay'}
        </button>
        <button data-testid="sketch-zoom-out" onClick={() => zoomBy(0.85)}
          className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>−</button>
        <button data-testid="sketch-zoom-reset" onClick={() => setView({ tx: 0, ty: 0, k: 1 })}
          className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>reset</button>
        <button data-testid="sketch-zoom-in" onClick={() => zoomBy(1.18)}
          className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>+</button>
        <button data-testid="control-canvas-clear" onClick={() => { if (confirm('Clear all blocks?')) clearAll(); }}
          className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>clear</button>
        <button data-testid="control-canvas-close" onClick={onClose}
          className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>close</button>
      </div>
      <div
        ref={surfaceRef}
        data-testid="canvas-surface"
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        className="flex-1 relative overflow-hidden"
        style={{
          cursor: 'crosshair',
          touchAction: 'none',
          backgroundImage: 'radial-gradient(circle, rgba(141,139,147,.18) 1px, transparent 1px)',
          backgroundSize: `${28 * view.k}px ${28 * view.k}px`,
          backgroundPosition: `${view.tx}px ${view.ty}px`,
        }}
      >
        <div ref={viewRef} className="absolute top-0 left-0"
          style={{ transform: `translate(${view.tx}px, ${view.ty}px) scale(${view.k})`, transformOrigin: '0 0' }}>
          {blocks.map(b => <Block key={b.id} b={b} zoom={view.k} />)}
        </div>
        {blocks.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-[15px]" style={{ color: 'var(--text-muted)' }}>click anywhere — start writing · ⠿ drag to move · shift-click to select</span>
          </div>
        )}
        <div className="absolute right-3 bottom-3 text-[11px] font-mono pointer-events-none" style={{ color: 'var(--text-muted)' }}>
          z{view.k.toFixed(2)} · {blocks.length} blocks
        </div>
      </div>
    </div>
  );
}
