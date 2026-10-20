/**
 * Deterministic tree layout for the argument canvas.
 * No randomness, no LLM coordinates — ClaimGraph principle 7:
 * "Layout is deterministic application code, not generated coordinates."
 *
 * Left-to-right tree: roots at x=0, each depth level +H_GAP, siblings
 * stacked vertically with V_GAP between them. Children computed after
 * parents so the layout is stable regardless of node insertion order.
 */

export interface LayoutNode {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface LayoutEdge {
  from: string;
  to: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface Layout {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  width: number;
  height: number;
}

const NODE_W = 260;
const NODE_H = 72;
const H_GAP = 320;
const V_GAP = 100;
const PAD = 40;

interface GraphNode {
  id: string;
  kind: string;
  text?: string;
}
interface GraphEdge {
  from: string;
  to: string;
  rel: string;
}

/** Build adjacency: children = nodes pointing AT this node (evidence → claim),
 * plus follows-targets (the next question in the chain). */
function childrenMap(nodes: GraphNode[], edges: GraphEdge[]): Map<string, string[]> {
  const m = new Map<string, string[]>();
  for (const n of nodes) m.set(n.id, []);
  for (const e of edges) {
    if (!m.has(e.to)) m.set(e.to, []);
    m.get(e.to)!.push(e.from); // e.from is a child (evidence/answer pointing at e.to)
  }
  for (const e of edges) {
    if (e.rel === 'follows') {
      if (!m.has(e.from)) m.set(e.from, []);
      m.get(e.from)!.push(e.to); // follows-target is also a child (chain)
    }
  }
  return m;
}

function rootsOf(nodes: GraphNode[], edges: GraphEdge[]): string[] {
  const follows = new Set(edges.filter(e => e.rel === 'follows').map(e => e.to));
  const roots = nodes.filter(n => n.kind === 'question' && !follows.has(n.id)).map(n => n.id);
  if (roots.length > 0) return roots;
  const noIncoming = new Set(edges.map(e => e.to));
  const orphans = nodes.filter(n => !noIncoming.has(n.id)).map(n => n.id);
  return orphans.length > 0 ? orphans : nodes.slice(0, 1).map(n => n.id);
}

export function layoutTree(
  nodes: GraphNode[],
  edges: GraphEdge[],
  order: Record<string, number> = { question: 0, claim: 1, resolution: 2, quote: 3, gap: 4 },
): Layout {
  const cmap = childrenMap(nodes, edges);
  const byId = new Map(nodes.map(n => [n.id, n]));
  const visited = new Set<string>();
  const result: LayoutNode[] = [];
  let cursorY = 0;

  // Depth-first: assign y to each leaf, parent y = midpoint of children.
  function place(id: string, depth: number): number {
    if (visited.has(id)) return cursorY;
    visited.add(id);
    const kids = (cmap.get(id) || [])
      .filter(k => byId.has(k))
      .sort((a, b) => (order[byId.get(a)!.kind] ?? 9) - (order[byId.get(b)!.kind] ?? 9));
    const y =
      kids.length === 0
        ? cursorY++
        : (() => {
            const ys = kids.map(k => place(k, depth + 1));
            return (Math.min(...ys) + Math.max(...ys)) / 2;
          })();
    result.push({ id, x: PAD + depth * H_GAP, y: PAD + y * V_GAP, w: NODE_W, h: NODE_H });
    return y;
  }

  for (const r of rootsOf(nodes, edges)) place(r, 0);

  // Any unreachable nodes (orphans with incoming edges) get placed below.
  for (const n of nodes) {
    if (!visited.has(n.id)) {
      visited.add(n.id);
      result.push({ id: n.id, x: PAD, y: PAD + cursorY++ * V_GAP, w: NODE_W, h: NODE_H });
    }
  }

  const width = Math.max(...result.map(n => n.x + n.w), 400) + PAD;
  const height = Math.max(...result.map(n => n.y + n.h), 300) + PAD;

  const posMap = new Map(result.map(n => [n.id, n]));
  const ledges: LayoutEdge[] = edges
    .filter(e => posMap.has(e.from) && posMap.has(e.to))
    .map(e => {
      const a = posMap.get(e.from)!;
      const b = posMap.get(e.to)!;
      return { from: e.from, to: e.to, x1: a.x + a.w, y1: a.y + a.h / 2, x2: b.x, y2: b.y + b.h / 2 };
    });

  return { nodes: result, edges: ledges, width, height };
}
