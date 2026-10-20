import { create } from 'zustand';
import * as secureStorage from '../services/secureStorage';

const KEY = 'quill-arguments-v1';

export type ArgKind = 'question' | 'claim' | 'quote' | 'resolution' | 'gap';
export type ArgRel = 'answers' | 'supports' | 'resolves' | 'leaves-open' | 'follows';

export interface ArgNode {
  id: string;
  kind: ArgKind;
  text: string;
  source?: { file: string; line: number };
}

export interface ArgEdge {
  from: string;
  to: string;
  rel: ArgRel;
}

export interface ArgGraph {
  name: string;
  nodes: ArgNode[];
  edges: ArgEdge[];
  /** node ids currently collapsed (children hidden) */
  collapsed: string[];
}

interface ArgumentState {
  graphs: ArgGraph[];
  setGraphs: (g: ArgGraph[]) => void;
  toggle: (gi: number, id: string) => void;
  clear: () => void;
  persist: () => Promise<void>;
  initialize: () => Promise<void>;
}

/** Roots: top-level questions (never the target of a 'follows' edge).
 * Children of X: evidence/answers pointing at X, plus gaps X leaves open,
 * plus the next question in the chain ('follows'). Quotes are always
 * leaves; gaps always stem from their source. */
export function childrenOf(g: ArgGraph, id: string): ArgNode[] {
  const kids: ArgNode[] = [];
  for (const e of g.edges) {
    if (e.to === id && e.rel !== 'follows') {
      const n = g.nodes.find(n => n.id === e.from);
      if (n && !kids.some(k => k.id === n.id)) kids.push(n);
    }
  }
  for (const e of g.edges) {
    if (e.from === id && (e.rel === 'follows' || e.rel === 'leaves-open')) {
      const n = g.nodes.find(n => n.id === e.to);
      if (n && !kids.some(k => k.id === n.id)) kids.push(n);
    }
  }
  // Stable order: questions, claims, resolutions, quotes, gaps — chain reads top-down.
  const order: Record<ArgKind, number> = { question: 0, claim: 1, resolution: 2, quote: 3, gap: 4 };
  return kids.sort((a, b) => order[a.kind] - order[b.kind]);
}

export function rootsOf(g: ArgGraph): ArgNode[] {
  const followed = new Set(g.edges.filter(e => e.rel === 'follows').map(e => e.to));
  const roots = g.nodes.filter(n => n.kind === 'question' && !followed.has(n.id));
  if (roots.length > 0) return roots;
  const noIncoming = new Set(g.edges.map(e => e.to));
  const orphans = g.nodes.filter(n => !noIncoming.has(n.id));
  return orphans.length > 0 ? orphans : g.nodes.slice(0, 1);
}

const EMPTY: { graphs: ArgGraph[] } = { graphs: [] };

export const useArgumentStore = create<ArgumentState>()((set, get) => ({
  graphs: [],
  setGraphs: (graphs) => { set({ graphs }); void get().persist(); },
  toggle: (gi, id) => {
    set(s => {
      const graphs = s.graphs.map((g, i) => {
        if (i !== gi) return g;
        const collapsed = g.collapsed.includes(id)
          ? g.collapsed.filter(c => c !== id)
          : [...g.collapsed, id];
        return { ...g, collapsed };
      });
      return { graphs };
    });
    void get().persist();
  },
  clear: () => { set({ graphs: [] }); void secureStorage.removeItem(KEY); },
  persist: async () => {
    await secureStorage.setItem(KEY, JSON.stringify(get().graphs));
  },
  initialize: async () => {
    try {
      const raw = await secureStorage.getItem(KEY);
      if (!raw) return;
      const graphs = JSON.parse(raw) as ArgGraph[];
      if (Array.isArray(graphs)) set({ graphs });
    } catch { /* fresh args on corrupt storage */ }
  },
}));
