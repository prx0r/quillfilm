import { describe, expect, it } from 'vitest';
import { nextStatus, parseStoryboardTables } from './storyboard';

const SHOT_TABLE = `## EXPOSITION (0:00–4:00)

| # | t0–t1 | Visual | Audio | Overlay data | Dur |
|---|---|---|---|---|---|
| S01 | 0:00–0:45 | Dark room, standing mirror | room tone + one struck bell | title only | 45s |
| S02 | 0:45–1:15 | Black + flame-motif micro-echo | [CH.2 opener lines, script] | none | 30s |
`;

const BEAT_TABLE = `# MOVIE — "Change of Clothes" (Hindu · ~20 min)

## Beat table
| # | t | Beat | Rhythm |
|---|---|---|---|
| B1 | 0:00–0:45 | SCENE: dawn wardrobe | slow, no cuts |
| B2 | 0:45–2:30 | Two-layers: atman + karma-steering | 3 cuts |
`;

const NON_BOARD = `# WEAVE — quote bank

| Field | Content |
|---|---|
| WHAT | the theory in one breath |
`;

describe('parseStoryboardTables', () => {
  it('parses shot tables with ids, times, visuals, audio and act', () => {
    const rows = parseStoryboardTables(SHOT_TABLE);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ id: 'S01', time: '0:00–0:45', act: 'EXPOSITION' });
    expect(rows[0].visual).toContain('standing mirror');
    expect(rows[1].audio).toContain('CH.2 opener');
  });

  it('parses MOVIE.md beat tables', () => {
    const rows = parseStoryboardTables(BEAT_TABLE);
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({ id: 'B1', time: '0:00–0:45' });
    expect(rows[0].visual).toContain('dawn wardrobe');
  });

  it('skips tables without shot ids', () => {
    expect(parseStoryboardTables(NON_BOARD)).toEqual([]);
  });

  it('skips prose and keeps act per section', () => {
    const md = `# Film\n\nSome prose about nothing.\n\n${SHOT_TABLE}\n\n## DEVELOPMENT (4:00–9:45)\n\n| # | t0–t1 | Visual | Audio |\n|---|---|---|---|\n| S05 | 4:00–5:15 | Axe scene | bell |\n`;
    const rows = parseStoryboardTables(md);
    expect(rows.map(r => r.id)).toEqual(['S01', 'S02', 'S05']);
    expect(rows[2].act).toBe('DEVELOPMENT');
  });
});

describe('nextStatus', () => {
  it('advances draft → locked → done and stays done', () => {
    expect(nextStatus('draft')).toBe('locked');
    expect(nextStatus('locked')).toBe('done');
    expect(nextStatus('done')).toBe('done');
  });
});
