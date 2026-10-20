import { describe, expect, it } from 'vitest';
import { parseCards } from './canvasPull';

describe('parseCards (typed payload — opencanvas law)', () => {
  it('parses a clean array', () => {
    const r = parseCards('[{"k":"quote","t":"Karma is the field.","src":"WEAVE K2"},{"k":"next","t":"Who then?"}]');
    expect(r).toHaveLength(2);
    expect(r[0]).toEqual({ k: 'quote', t: 'Karma is the field.', src: 'WEAVE K2' });
  });
  it('survives fences and surrounding prose', () => {
    const r = parseCards('Here are cards:\n```json\n[{"k":"objection","t":"unsourced claim"}]\n```');
    expect(r).toHaveLength(1);
    expect(r[0].k).toBe('objection');
  });
  it('drops malformed kinds and empty text', () => {
    const r = parseCards('[{"k":"poem","t":"x"},{"k":"quote","t":""},{"k":"quote","t":"ok"}]');
    expect(r).toHaveLength(1);
    expect(r[0].t).toBe('ok');
  });
  it('returns [] on garbage — quiet canvas beats an error', () => {
    expect(parseCards('no json here')).toEqual([]);
    expect(parseCards('{"k":"quote"}')).toEqual([]);
  });
  it('caps at 4 cards and 240 chars', () => {
    const many = JSON.stringify(Array.from({ length: 8 }, (_, i) => ({ k: 'next', t: 'q'.repeat(300) + i })));
    const r = parseCards(many);
    expect(r).toHaveLength(4);
    expect(r[0].t.length).toBeLessThanOrEqual(240);
  });
});
