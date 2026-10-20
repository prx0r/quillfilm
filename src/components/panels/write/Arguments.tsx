import { childrenOf, rootsOf, useArgumentStore, type ArgGraph, type ArgKind } from '../../../stores/useArgumentStore';

const KIND_STYLE: Record<ArgKind, { label: string; color: string; serif?: boolean }> = {
  question: { label: 'Q', color: '#F5C76B' },
  claim: { label: '◦', color: '#f3f1ec' },
  quote: { label: '“”', color: '#F5C76B', serif: true },
  resolution: { label: '✓', color: '#5EC4B6' },
  gap: { label: '?', color: '#E8102E' },
};

function Node({ g, gi, id, depth }: { g: ArgGraph; gi: number; id: string; depth: number }) {
  const toggle = useArgumentStore(s => s.toggle);
  const node = g.nodes.find(n => n.id === id);
  if (!node) return null;
  const kids = childrenOf(g, id);
  const collapsed = g.collapsed.includes(id);
  const st = KIND_STYLE[node.kind];
  return (
    <div style={{ marginLeft: depth === 0 ? 0 : 14, borderLeft: depth === 0 ? undefined : '1px solid var(--border)', paddingLeft: depth === 0 ? 0 : 8 }}>
      <div className="flex items-start gap-1.5 py-1">
        {kids.length > 0 && (
          <button data-testid="control-arg-toggle" onClick={() => toggle(gi, id)} aria-label={collapsed ? 'Expand' : 'Collapse'}
            className="text-[11px] font-mono w-4 shrink-0 text-center" style={{ color: 'var(--text-muted)' }}>
            {collapsed ? '+' : '–'}
          </button>
        )}
        <span className="text-[11px] font-mono w-6 shrink-0 pt-px" style={{ color: st.color }} title={node.kind}>{st.label}</span>
        <div className="text-[12px] leading-snug" style={st.serif ? { color: '#F5C76B', fontFamily: 'Georgia, serif' } : { color: 'var(--text-primary)' }}>
          {node.text}
          {node.source && (
            <span className="text-[10px] font-mono ml-1" style={{ color: 'var(--text-muted)' }}>
              [{node.source.file.split('/').pop()}:{node.source.line}]
            </span>
          )}
        </div>
      </div>
      {!collapsed && kids.map(k => <Node key={k.id} g={g} gi={gi} id={k.id} depth={depth + 1} />)}
    </div>
  );
}

/** Arguments view: reasoning branches from the pack's argument graphs.
 * Verbatim quotes render serif + gold (citation law); gaps render red as
 * unresolved. Click a node to collapse/expand its branch. */
export function Arguments() {
  const graphs = useArgumentStore(s => s.graphs);
  if (graphs.length === 0) {
    return (
      <p className="text-[13px]" style={{ color: 'var(--text-muted)' }}>
        No argument graphs loaded. Load a pack with reasoning chains (karma, film-saiva) and they branch here.
      </p>
    );
  }
  return (
    <div className="space-y-4 max-h-96 overflow-auto" data-testid="arguments-view">
      {graphs.map((g, gi) => (
        <div key={`${g.name}-${gi}`}>
          <div className="text-[12px] font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>{g.name}</div>
          {rootsOf(g).map(r => <Node key={r.id} g={g} gi={gi} id={r.id} depth={0} />)}
        </div>
      ))}
    </div>
  );
}
