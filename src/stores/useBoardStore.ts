import { create } from 'zustand';
import { nextStatus, type ShotRow, type ShotStatus } from '../services/storyboard';
import * as secureStorage from '../services/secureStorage';

const KEY = 'quill-board-v1';

export interface BoardState {
  packSlug: string;
  packTitle: string;
  rows: ShotRow[];
  journey: string[];
  updatedAt: number;
}

interface BoardStore extends BoardState {
  setBoard: (b: BoardState) => void;
  advance: (id: string) => void;
  logJourney: (entry: string) => void;
  clear: () => void;
  persist: () => Promise<void>;
  initialize: () => Promise<void>;
}

const EMPTY: BoardState = { packSlug: '', packTitle: '', rows: [], journey: [], updatedAt: 0 };

export const useBoardStore = create<BoardStore>()((set, get) => ({
  ...EMPTY,
  setBoard: (b) => { set(b); void get().persist(); },
  advance: (id) => {
    const st = get();
    const rows = st.rows.map(r => r.id === id ? { ...r, status: nextStatus(r.status) } : r);
    const changed = rows.find(r => r.id === id);
    const journey = changed && changed.status === 'done'
      ? [...st.journey, `${new Date().toISOString().slice(0, 16).replace('T', ' ')} — marked ${id} done${changed.time ? ` (${changed.time})` : ''}`]
      : st.journey;
    set({ rows, journey, updatedAt: Date.now() });
    void get().persist();
  },
  logJourney: (entry) => {
    set(s => ({ journey: [...s.journey, entry], updatedAt: Date.now() }));
    void get().persist();
  },
  clear: () => { set(EMPTY); void secureStorage.removeItem(KEY); },
  persist: async () => {
    const { packSlug, packTitle, rows, journey, updatedAt } = get();
    await secureStorage.setItem(KEY, JSON.stringify({ packSlug, packTitle, rows, journey, updatedAt }));
  },
  initialize: async () => {
    try {
      const raw = await secureStorage.getItem(KEY);
      if (!raw) return;
      const data = JSON.parse(raw) as BoardState;
      if (Array.isArray(data.rows)) set({ ...EMPTY, ...data });
    } catch { /* fresh board on corrupt storage */ }
  },
}));

/** Render the board + journey log as markdown (render-pipeline handoff, JOURNEY.md seed). */
export function boardToMarkdown(b: BoardState): string {
  const lines = [`# Board — ${b.packTitle || 'untitled'} (${b.packSlug || 'no pack'})`, ''];
  let act = '';
  for (const r of b.rows) {
    if (r.act && r.act !== act) { act = r.act; lines.push(`## ${act}`, ''); }
    const box = r.status === 'done' ? '[x]' : r.status === 'locked' ? '[~]' : '[ ]';
    lines.push(`- ${box} **${r.id}**${r.time ? ` \`${r.time}\`` : ''} — ${r.visual}`);
    if (r.audio) lines.push(`  - audio: ${r.audio.slice(0, 160)}`);
  }
  if (b.journey.length) {
    lines.push('', '## Journey log', '');
    for (const j of b.journey) lines.push(`- ${j}`);
  }
  return lines.join('\n');
}

/** Machine form for the render queue. */
export function boardToJson(b: BoardState): string {
  return JSON.stringify({ pack: b.packSlug, title: b.packTitle, updatedAt: b.updatedAt, rows: b.rows }, null, 1);
}

export type { ShotStatus };
