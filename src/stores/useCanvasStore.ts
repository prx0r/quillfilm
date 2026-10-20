import { create } from 'zustand';
import * as secureStorage from '../services/secureStorage';
import type { CanvasCard } from '../services/canvasPull';

const KEY = 'quill-canvas-v1';

export interface CanvasBlock {
  id: string;
  x: number;
  y: number;
  text: string;
  cards: CanvasCard[];
  pulling: boolean;
  pulled: boolean; // pause-pull already ran for this text version
}

interface CanvasStore {
  blocks: CanvasBlock[];
  /** shift-click selection: drag one handle to move the whole set */
  selected: string[];
  packSlug: string;
  open: boolean;
  setOpen: (v: boolean) => void;
  addBlock: (x: number, y: number) => void;
  updateText: (id: string, text: string) => void;
  setCards: (id: string, cards: CanvasCard[]) => void;
  setPulling: (id: string, v: boolean) => void;
  markPulled: (id: string) => void;
  removeBlock: (id: string) => void;
  /** absolute world positions; persist=false while dragging (one save on drop) */
  applyPositions: (entries: Array<{ id: string; x: number; y: number }>, persist?: boolean) => void;
  toggleSelect: (id: string, additive: boolean) => void;
  clearSelection: () => void;
  clearAll: () => void;
  setPack: (slug: string) => void;
  persist: () => Promise<void>;
  initialize: () => Promise<void>;
}

const EMPTY = { blocks: [] as CanvasBlock[], selected: [] as string[], packSlug: '', open: false };

export const useCanvasStore = create<CanvasStore>()((set, get) => ({
  ...EMPTY,
  setOpen: (v) => set({ open: v }),
  addBlock: (x, y) => {
    const b: CanvasBlock = { id: `b${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`, x, y, text: '', cards: [], pulling: false, pulled: false };
    set(s => ({ blocks: [...s.blocks, b] }));
    void get().persist();
  },
  updateText: (id, text) => {
    set(s => ({ blocks: s.blocks.map(b => (b.id === id ? { ...b, text } : b)) }));
    void get().persist();
  },
  setCards: (id, cards) => {
    set(s => ({ blocks: s.blocks.map(b => (b.id === id ? { ...b, cards, pulling: false } : b)) }));
    void get().persist();
  },
  setPulling: (id, v) => set(s => ({ blocks: s.blocks.map(b => (b.id === id ? { ...b, pulling: v } : b)) })),
  markPulled: (id) => set(s => ({ blocks: s.blocks.map(b => (b.id === id ? { ...b, pulled: true } : b)) })),
  applyPositions: (entries, persist = true) => {
    const m = new Map(entries.map(e => [e.id, e]));
    set(s => ({ blocks: s.blocks.map(b => (m.has(b.id) ? { ...b, ...m.get(b.id)! } : b)) }));
    if (persist) void get().persist();
  },
  toggleSelect: (id, additive) => {
    set(s => {
      if (!additive) return { selected: s.selected.length === 1 && s.selected[0] === id ? [] : [id] };
      return { selected: s.selected.includes(id) ? s.selected.filter(x => x !== id) : [...s.selected, id] };
    });
  },
  clearSelection: () => set({ selected: [] }),
  removeBlock: (id) => {
    set(s => ({ blocks: s.blocks.filter(b => b.id !== id), selected: s.selected.filter(x => x !== id) }));
    void get().persist();
  },
  clearAll: () => { set({ blocks: [], selected: [] }); void get().persist(); },
  setPack: (slug) => { set({ packSlug: slug }); void get().persist(); },
  persist: async () => {
    const { blocks, packSlug } = get();
    await secureStorage.setItem(KEY, JSON.stringify({ blocks, packSlug }));
  },
  initialize: async () => {
    try {
      const raw = await secureStorage.getItem(KEY);
      if (!raw) return;
      const d = JSON.parse(raw);
      if (Array.isArray(d.blocks)) set({ blocks: d.blocks, packSlug: d.packSlug || '' });
    } catch { /* fresh canvas */ }
  },
}));
