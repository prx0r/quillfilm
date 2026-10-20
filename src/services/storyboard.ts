/** Storyboard tables → shot rows for the Board view.
 * Parses the two table shapes our packs use (shot tables with SNN ids and
 * MOVIE.md beat tables with BNN ids). Unknown tables are skipped, never
 * guessed: a row needs an id cell to exist.
 */

export type ShotStatus = 'draft' | 'locked' | 'done';

export interface ShotRow {
  id: string;
  time: string;
  visual: string;
  audio: string;
  act: string;
  status: ShotStatus;
}

const splitRow = (line: string): string[] =>
  line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());

const isSeparator = (line: string): boolean =>
  /^\|?[\s:|-]+\|[\s:|-]*\|?/.test(line.trim()) && line.includes('-');

function columnRole(header: string): 'id' | 'time' | 'visual' | 'audio' | null {
  const h = header.toLowerCase();
  if (/^(#|shot|no\.?|s(e)?[0-9]*)$/.test(h)) return 'id';
  if (/t0|t[–-]t/.test(h) || /^(t|time|timing|slot|dur|duration)$/.test(h)) return 'time';
  if (/visual|beat|shot|scene|image|dir/.test(h)) return 'visual';
  if (/audio|vo|narrat|speak|sound|say/.test(h)) return 'audio';
  return null;
}

/** Parse every markdown table with an id column into shot rows. */
export function parseStoryboardTables(md: string): Omit<ShotRow, 'status'>[] {
  const rows: Omit<ShotRow, 'status'>[] = [];
  const lines = md.split('\n');
  let act = '';
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const heading = line.match(/^#{1,4}\s+(.+?)\s*$/);
    if (heading && !line.includes('|')) {
      act = heading[1].replace(/\s*\(?\d+:\d+.*$/, '').trim().slice(0, 80);
      continue;
    }
    if (!line.trim().startsWith('|')) continue;
    if (i + 1 >= lines.length || !isSeparator(lines[i + 1])) continue;
    const headers = splitRow(line);
    const roles = headers.map(columnRole);
    if (!roles.includes('id')) { i++; continue; }
    const idIdx = roles.indexOf('id');
    const timeIdx = roles.indexOf('time');
    const visIdx = roles.indexOf('visual');
    const audIdx = roles.indexOf('audio');
    i += 2;
    while (i < lines.length && lines[i].trim().startsWith('|') && !isSeparator(lines[i])) {
      const cells = splitRow(lines[i]);
      const id = (cells[idIdx] || '').replace(/\*\*/g, '').trim();
      if (/^[SB]?\d{1,3}[a-z]?$/i.test(id) || /^S\d/i.test(id)) {
        rows.push({
          id: id.toUpperCase(),
          time: timeIdx >= 0 ? (cells[timeIdx] || '') : '',
          visual: visIdx >= 0 ? (cells[visIdx] || '') : '',
          audio: audIdx >= 0 ? (cells[audIdx] || '') : '',
          act,
        });
      }
      i++;
    }
    i--;
  }
  return rows;
}

/** Advance draft → locked → done (done is terminal). */
export function nextStatus(s: ShotStatus): ShotStatus {
  return s === 'draft' ? 'locked' : s === 'locked' ? 'done' : 'done';
}
