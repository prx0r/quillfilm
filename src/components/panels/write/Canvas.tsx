import { useEffect, useRef, useState } from 'react';
import { layoutTree, type LayoutNode } from '../../../services/argumentLayout';
import { useArgumentStore, type ArgKind } from '../../../stores/useArgumentStore';

const KIND_FILL: Record<ArgKind, { bg: string; fg: string }> = {
  question: { bg: 'rgba(245,199,107,.12)', fg: '#F5C76B' },
  claim:    { bg: 'rgba(243,241,236,.06)', fg: '#f3f1ec' },
  quote:    { bg: 'rgba(245,199,107,.10)', fg: '#F5C76B' },
  resolution:{ bg: 'rgba(94,196,182,.10)', fg: '#5EC4B6' },
  gap:      { bg: 'rgba(232,16,46,.10)', fg: '#E8102E' },
};
const REL_STROKE: Record<string, string> = {
  answers: '#5EC4B6', supports: '#F5C76B', resolves: '#5EC4B6',
  'leaves-open': '#E8102E', follows: '#8d8b93',
};

function wrapText(text: string, max: number): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).trim().length > max && cur) { lines.push(cur); cur = w; }
    else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  return lines.slice(0, 4); // 4 lines max inside the box
}

function CanvasNode({ n, node, selected, onSelect }: {
  n: LayoutNode; node: { kind: ArgKind; text: string; source?: { file: string; line: number } };
  selected: boolean; onSelect: (id: string) => void;
}) {
  const fill = KIND_FILL[node.kind] || KIND_FILL.claim;
  const lines = wrapText(node.text, 34);
  return (
    <g transform={`translate(${n.x},${n.y})`} style={{ cursor: 'pointer' }} onClick={() => onSelect(n.id)}>
      <rect width={n.w} height={n.h} rx={10} fill={fill.bg} stroke={selected ? '#F5C76B' : '#2a2a33'} strokeWidth={selected ? 2 : 1}/>
      <rect width={4} height={n.h} rx={2} fill={fill.fg}/>
      <text x={14} y={20} fontSize={11} fill={fill.fg} fontWeight={700} fontFamily="ui-monospace,monospace">
        {node.kind.toUpperCase()}
      </text>
      {lines.map((l, i) => (
        <text key={i} x={14} y={38 + i * 14} fontSize={12} fill="#f3f1ec" fontFamily="Inter,system-ui,sans-serif">
          {l}{i === 3 && node.text.split(/\s+/).length > 130 ? '…' : ''}
        </text>
      ))}
      {node.source && (
        <text x={n.w - 8} y={n.h - 6} fontSize={9} fill="#8d8b93" textAnchor="end" fontFamily="ui-monospace,monospace">
          {node.source.file.split('/').pop()}:{node.source.line}
        </text>
      )}
    </g>
  );
}

/** Canvas view: deterministic spatial layout of argument graphs.
 * Pan: drag. Zoom: wheel. Click: select node (detail panel below).
 * No LLM coordinates — ClaimGraph principle 7. */
export function Canvas() {
  const graphs = useArgumentStore(s => s.graphs);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const dragRef = useRef<{ sx: number; sy: number; vx: number; vy: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const active = graphs[0]; // v1: first loaded graph
  const layout = active ? layoutTree(active.nodes, active.edges) : null;

  useEffect(() => { setView({ x: 0, y: 0, k: 1 }); setSelected(null); }, [active?.name]);

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setView(v => ({ ...v, k: Math.min(3, Math.max(0.3, v.k * delta)) }));
  };
  const onDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    (e.target as Element).setPointerCapture?.(e.pointerId);
    dragRef.current = { sx: e.clientX, sy: e.clientY, vx: view.x, vy: view.y };
  };
  const onMove = (e: React.PointerEvent) => {
    if (!dragRef.current) return;
    const d = dragRef.current;
    setView(v => ({ ...v, x: d.vx + (e.clientX - d.sx), y: d.vy + (e.clientY - d.sy) }));
  };
  const onUp = () => { dragRef.current = null; };

  const selNode = selected ? active?.nodes.find(n => n.id === selected) : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[13px] font-semibold" style={{ color: 'var(--text-primary)' }}>{active?.name || 'no graphs loaded'}</span>
        <div className="flex gap-1">
          <button data-testid="control-canvas-zoom-out" onClick={() => setView(v => ({ ...v, k: Math.max(0.3, v.k * 0.85) }))} className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>−</button>
          <button data-testid="control-canvas-reset" onClick={() => setView({ x: 0, y: 0, k: 1 })} className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>reset</button>
          <button data-testid="control-canvas-zoom-in" onClick={() => setView(v => ({ ...v, k: Math.min(3, v.k * 1.2) }))} className="text-[11px] px-2 py-1 rounded border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>+</button>
        </div>
      </div>
      {!layout ? (
        <p className="text-[13px]" style={{ color: 'var(--text-muted)' }}>No graphs loaded. Load a pack with reasoning chains (karma, film-saiva) and they branch here.</p>
      ) : (
      <>
      <svg
        ref={svgRef}
        data-testid="argument-canvas"
        width="100%"
        height={340}
        style={{ background: '#0b0b10', border: '1px solid var(--border)', borderRadius: 12, cursor: 'grab', touchAction: 'none' }}
        onWheel={onWheel}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerLeave={onUp}
      >
        <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
          {layout!.edges.map((e, i) => (
            <path
              key={i}
              d={`M ${e.x1} ${e.y1} C ${e.x1 + 60} ${e.y1}, ${e.x2 - 60} ${e.y2}, ${e.x2} ${e.y2}`}
              fill="none"
              stroke={REL_STROKE[active!.edges[i]?.rel] || '#2a2a33'}
              strokeWidth={1.5}
              strokeDasharray={active!.edges[i]?.rel === 'leaves-open' ? '4 3' : undefined}
              opacity={0.7}
            />
          ))}
          {layout!.nodes.map(n => {
            const node = active!.nodes.find(x => x.id === n.id)!;
            if (!node) return null;
            return <CanvasNode key={n.id} n={n} node={node} selected={selected === n.id} onSelect={setSelected} />;
          })}
        </g>
      </svg>
      {selNode && (
        <div className="mt-2 p-3 rounded-lg border text-[13px]" style={{ borderColor: 'var(--border)', background: 'var(--surface-1, #111116)' }}>
          <div className="text-[11px] font-mono mb-1" style={{ color: KIND_FILL[selNode.kind]?.fg || '#f3f1ec' }}>{selNode.kind.toUpperCase()}</div>
          <div style={{ color: 'var(--text-primary)' }}>{selNode.text}</div>
          {selNode.source && <div className="text-[10px] font-mono mt-1" style={{ color: 'var(--text-muted)' }}>{selNode.source.file}:{selNode.source.line}</div>}
        </div>
      )}
      </>
      )}
    </div>
  );
}
