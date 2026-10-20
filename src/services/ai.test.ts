import { describe, it, expect } from 'vitest';
import {
  parseJSONRobust,
  anchorSuggestions,
  lintSuggestedText,
  buildConflictGroups,
  detectH2Sections,
  stripThinkingBlocks,
  countWords,
  bestTrimCandidate,
  isAdvisoryAgent,
  ADVISORY_AGENTS,
  spansOverlap,
  dedupeAdvisories,
  parseSweepCommand,
  buildSweepPrompt,
  lookupQuote,
  lookupClip,
  runBoardcheck,
  type ClipFetch,
} from './ai';
import type { Suggestion } from '../types';
import { looksLikeThinking, isForwardContinuation } from '../../scripts/eval/checks';

describe('parseJSONRobust', () => {
  it('parses clean JSON', () => {
    expect(parseJSONRobust('{"a":1}')).toEqual({ a: 1 });
  });
  it('extracts JSON from a markdown code fence', () => {
    expect(parseJSONRobust('```json\n{"a":1}\n```')).toEqual({ a: 1 });
  });
  it('tolerates trailing commas', () => {
    expect(parseJSONRobust('{"a":1,}')).toEqual({ a: 1 });
  });
  it('extracts a JSON object embedded in prose', () => {
    expect(parseJSONRobust('Sure! Here it is: {"a":1} hope that helps'))
      .toEqual({ a: 1 });
  });
  it('recovers individual suggestion objects from a truncated array', () => {
    const raw = '{"suggestions":[{"originalText":"x","suggestedText":"y"},{"originalText":"a","suggestedText":"b"}';
    const parsed = parseJSONRobust(raw);
    expect(parsed.suggestions.length).toBeGreaterThanOrEqual(1);
  });
  it('throws on hopeless input', () => {
    expect(() => parseJSONRobust('not json at all')).toThrow();
  });
});

describe('lintSuggestedText', () => {
  it('removes em and en dashes', () => {
    expect(lintSuggestedText('the result — robust — held', 'orig')).not.toMatch(/[—–]/);
  });
  it('keeps a tight en dash between numbers: it is a range, not the em-dash tell', () => {
    expect(lintSuggestedText('We used 10–20 nM ligand against H1–H3 [3–5].', 'orig')).toBe('We used 10–20 nM ligand against H1–H3 [3–5].');
  });
  it('keeps a tight en dash when only the right side is a digit (label-to-number range)', () => {
    expect(lintSuggestedText('See panels A–5 and [3]–5 here.', 'orig')).toBe('See panels A–5 and [3]–5 here.');
  });
  it('still replaces spaced and em dashes and tight dashes between words', () => {
    expect(lintSuggestedText('The result – robust—held, Smith–Jones agree.', 'orig')).not.toMatch(/[—–]/);
  });
  it('re-appends a citation marker the model dropped from the original', () => {
    const out = lintSuggestedText('We observed cell death.', 'It was observed that cells died [3].');
    expect(out).toContain('[3]');
  });
  it('places the re-appended marker before the trailing period', () => {
    const out = lintSuggestedText('We observed cell death.', 'cells died [3]');
    expect(out.endsWith('[3].') || out.endsWith('[3]')).toBe(true);
  });
  it('does not add markers when the replacement already keeps them', () => {
    const out = lintSuggestedText('We observed cell death [3].', 'cells died [3]');
    expect((out.match(/\[3\]/g) || []).length).toBe(1);
  });
});

describe('anchorSuggestions', () => {
  const doc = 'It was observed that the cells died rapidly after treatment.';

  it('anchors an exact-quote suggestion and rewrites originalText to the doc text', () => {
    const raw = [{ originalText: 'the cells died rapidly', suggestedText: 'the cells died within 2 h', explanation: 'add detail', severity: 'minor', category: 'clarity' }];
    const { suggestions, dropped } = anchorSuggestions(raw, doc, 'editor', 'p');
    expect(dropped).toBe(0);
    expect(suggestions).toHaveLength(1);
    expect(doc).toContain(suggestions[0].originalText);
    expect(suggestions[0].startIndex).toBeGreaterThanOrEqual(0);
  });

  it('drops a no-op edit that differs only by unicode punctuation', () => {
    const raw = [{ originalText: 'the cells died rapidly', suggestedText: 'the cells died rapidly', explanation: '', severity: 'minor', category: 'clarity' }];
    const { suggestions, dropped } = anchorSuggestions(raw, doc, 'editor', 'p');
    expect(suggestions).toHaveLength(0);
    expect(dropped).toBe(1);
  });

  it('drops a suggestion whose quote cannot be located', () => {
    const raw = [{ originalText: 'the mice were injected', suggestedText: 'the mice received saline', explanation: '', severity: 'minor', category: 'clarity' }];
    const { dropped } = anchorSuggestions(raw, doc, 'editor', 'p');
    expect(dropped).toBe(1);
  });

  it('anchors an advisory suggestion with no suggestedText and keeps the recommendation', () => {
    const raw = [{ kind: 'advisory', originalText: 'the cells died rapidly', explanation: 'no measurement given', recommendation: 'report the timescale', severity: 'major', category: 'statistics' }];
    const { suggestions, dropped } = anchorSuggestions(raw, doc, 'statistician', 'p');
    expect(dropped).toBe(0);
    expect(suggestions).toHaveLength(1);
    expect(suggestions[0].kind).toBe('advisory');
    expect(suggestions[0].suggestedText).toBe('');
    expect(suggestions[0].recommendation).toBe('report the timescale');
    expect(doc).toContain(suggestions[0].originalText);
  });

  it('does NOT drop an advisory whose quote equals the source (no no-op rule)', () => {
    const raw = [{ kind: 'advisory', originalText: 'the cells died rapidly', explanation: 'x', recommendation: 'y', severity: 'minor', category: 'statistics' }];
    const { suggestions, dropped } = anchorSuggestions(raw, doc, 'statistician', 'p');
    expect(suggestions).toHaveLength(1);
    expect(dropped).toBe(0);
  });

  it('salvages a lightly misquoted suggestion via fuzzy match', () => {
    const raw = [{ originalText: 'It was observed that the cells perished rapidly after treatment', suggestedText: 'We observed rapid cell death after treatment', explanation: '', severity: 'major', category: 'clarity' }];
    const { suggestions, salvaged } = anchorSuggestions(raw, doc, 'editor', 'p');
    expect(suggestions.length + salvaged).toBeGreaterThan(0);
  });

  it('defaults invalid severity/category to safe values', () => {
    const raw = [{ originalText: 'the cells died rapidly', suggestedText: 'the cells died within hours', explanation: '', severity: 'catastrophic', category: 'vibes' }];
    const { suggestions } = anchorSuggestions(raw, doc, 'editor', 'p');
    expect(suggestions[0].severity).toBe('minor');
    expect(suggestions[0].category).toBe('clarity');
  });
});

describe('buildConflictGroups', () => {
  const mk = (id: string, start: number, end: number, original: string): Suggestion => ({
    id, originalText: original, suggestedText: 'x', explanation: '', agent: 'editor', startIndex: start, endIndex: end,
  });

  it('groups suggestions whose ranges overlap', () => {
    const groups = buildConflictGroups([
      mk('a', 0, 10, 'foo'),
      mk('b', 5, 15, 'bar'),
      mk('c', 100, 110, 'baz'),
    ]);
    // a and b overlap; c is alone
    const sizes = groups.map(g => g.length).sort();
    expect(sizes).toEqual([1, 2]);
  });

  it('groups when one quote contains the other', () => {
    const groups = buildConflictGroups([
      mk('a', 0, 40, 'the cells died rapidly after treatment'),
      mk('b', 200, 210, 'cells died'),
    ]);
    expect(groups.some(g => g.length === 2)).toBe(true);
  });
});

describe('detectH2Sections', () => {
  it('splits TipTap HTML on h2 headings in document order', () => {
    const html = '<h2>Introduction</h2><p>Intro body.</p><h2>Methods</h2><p>We did things.</p>';
    const secs = detectH2Sections(html);
    expect(secs.map(s => s.section)).toEqual(['Introduction', 'Methods']);
    expect(secs[1].text).toContain('We did things');
  });

  it('returns nothing when there are no h2 headings', () => {
    expect(detectH2Sections('<p>flat text</p>')).toEqual([]);
  });
});

describe('stripThinkingBlocks', () => {
  it('removes a bare "Thinking Process:" preamble and keeps the answer', () => {
    const input = 'Thinking Process:\nThe user wants a greeting.\n\nHello there.';
    expect(stripThinkingBlocks(input)).toBe('Hello there.');
  });
  it('keeps an unmarked numbered list even when prose follows (chat answer, not thinking)', () => {
    const input = '1. Analyze the request.\n2. Draft the reply.\n\nThe final answer.';
    expect(stripThinkingBlocks(input)).toBe(input);
  });
  it('strips a MARKED preamble with numbered reasoning steps, keeping the answer', () => {
    const input = 'Thinking Process:\n1. The user wants a summary.\n2. Keep it short.\n\nThe study shows a clear effect.';
    expect(stripThinkingBlocks(input)).toBe('The study shows a clear effect.');
  });
  it('leaves normal prose untouched', () => {
    expect(stripThinkingBlocks('A clean sentence.')).toBe('A clean sentence.');
  });
  it('keeps an unmarked numbered-list answer with no trailing prose', () => {
    const input = '1. The intro lacks a hypothesis.\n2. Methods omit sample size.\n3. Add effect sizes.';
    expect(stripThinkingBlocks(input)).toBe(input);
  });
  it('still discards a marked thinking block that has no answer', () => {
    expect(stripThinkingBlocks('Thinking Process:\n1. Consider the ask.\n2. Formulate a reply.')).toBe('');
  });
});

describe('countWords', () => {
  it('counts whitespace-delimited words', () => {
    expect(countWords('one two   three\nfour')).toBe(4);
  });
  it('is 0 for empty/whitespace', () => {
    expect(countWords('   ')).toBe(0);
  });
});

describe('bestTrimCandidate', () => {
  const input = 'w '.repeat(100).trim(); // 100 words
  it('prefers the longest candidate that is within budget', () => {
    const under50 = 'w '.repeat(40).trim();
    const under80 = 'w '.repeat(70).trim();
    const r = bestTrimCandidate(input, [under50, under80], 80);
    expect(r.text).toBe(under80);
    expect(r.withinBudget).toBe(true);
  });
  it('falls back to the shortest candidate when none meet budget', () => {
    const c90 = 'w '.repeat(90).trim();
    const c95 = 'w '.repeat(95).trim();
    const r = bestTrimCandidate(input, [c95, c90], 80);
    expect(r.text).toBe(c90);
    expect(r.withinBudget).toBe(false);
  });
  it('never returns text longer than the input', () => {
    const grew = 'w '.repeat(150).trim();
    const r = bestTrimCandidate(input, [grew], 80);
    expect(r.text).toBe(input); // all candidates grew -> return input
    expect(r.withinBudget).toBe(false);
  });
});

describe('eval predicates', () => {
  it('looksLikeThinking flags preambles', () => {
    expect(looksLikeThinking('Thinking Process: first I will...')).toBe(true);
    expect(looksLikeThinking('Sure! Here is the continuation.')).toBe(true);
    expect(looksLikeThinking(' and then the reaction proceeds.')).toBe(false);
  });
  it('isForwardContinuation rejects a verbatim restatement', () => {
    const ctx = 'The reaction proceeds at room temperature.';
    expect(isForwardContinuation(ctx, 'The reaction proceeds at room temperature.')).toBe(false);
    expect(isForwardContinuation(ctx, ' It then yields the product.')).toBe(true);
    expect(isForwardContinuation(ctx, '')).toBe(false);
  });
});

describe('advisory agent classification', () => {
  it('marks the data-dependent agents advisory by nature', () => {
    for (const a of ['statistician', 'consistency', 'reporting', 'reviewer-2', 'citation-checker'] as const) {
      expect(ADVISORY_AGENTS.has(a)).toBe(true);
      expect(isAdvisoryAgent(a)).toBe(true);
    }
  });
  it('leaves the text-quality agents as edit agents', () => {
    for (const a of ['editor', 'researcher', 'manager'] as const) {
      expect(isAdvisoryAgent(a)).toBe(false);
    }
  });
  it('adviceOnly override makes every agent advisory', () => {
    expect(isAdvisoryAgent('editor', { adviceOnly: true } as any)).toBe(true);
    expect(isAdvisoryAgent('manager', { adviceOnly: true } as any)).toBe(true);
  });
});

describe('dedupeAdvisories', () => {
  const mk = (id: string, text: string, start: number): Suggestion => ({
    id, originalText: text, suggestedText: '', explanation: '', recommendation: 'r',
    agent: 'statistician', startIndex: start, endIndex: start + text.length,
    kind: 'advisory', severity: 'major', category: 'statistics',
  });

  it('detects overlap by containment and by index range', () => {
    expect(spansOverlap(mk('a', 'the cells died rapidly', 5), mk('b', 'cells died', 9))).toBe(true);
    expect(spansOverlap(mk('a', 'foo', 0), mk('b', 'bar', 50))).toBe(false);
  });

  it('keeps the first (detector) advisory when two flag the same span', () => {
    const detector = mk('detector-0', 'p < 0.05 in the treated group', 10);
    const llm = mk('llm-1', 'p < 0.05', 10);
    const kept = dedupeAdvisories([detector, llm]);
    expect(kept).toHaveLength(1);
    expect(kept[0].id).toBe('detector-0');
  });

  it('keeps advisories on disjoint spans', () => {
    const kept = dedupeAdvisories([mk('a', 'foo', 0), mk('b', 'bar', 100)]);
    expect(kept).toHaveLength(2);
  });
});

describe('sweep command', () => {
  it('parses /sweep with and without focus', () => {
    expect(parseSweepCommand('/sweep')).toBe('');
    expect(parseSweepCommand('/sweep check the quotes')).toBe('check the quotes');
    expect(parseSweepCommand('  /sweep  tight  ')).toBe('tight');
    expect(parseSweepCommand('/sweepx')).toBeNull();
    expect(parseSweepCommand('please sweep this')).toBeNull();
  });

  it('builds the four-section contract with the section embedded', () => {
    const p = buildSweepPrompt('Yogacara', 'No soul, but a store. "Seeds" everywhere.', 'habits');
    expect(p).toContain('## Verdicts');
    expect(p).toContain('## READ checks');
    expect(p).toContain('## Implications');
    expect(p).toContain('## Drafts');
    expect(p).toContain('Yogacara');
    expect(p).toContain('No soul, but a store');
    expect(p).toContain('habits');
    expect(p).toContain('SILENT');
    expect(p).toContain('[DRAFT — owner to voice]');
  });

  it('works without title or focus', () => {
    const p = buildSweepPrompt(null, 'Some text here.');
    expect(p).toContain('Some text here.');
    expect(p).not.toContain('Sweep focus');
  });

  it('caps long sections', () => {
    const p = buildSweepPrompt('Big', 'x'.repeat(20000));
    expect(p.length).toBeLessThan(14000);
  });
});

describe('lookupQuote', () => {
  const srcs = [
    { name: 'WEAVE.md', text: '[K12] reeds — "two sheaves lean on each other" — SN 12.67' },
    { name: 'notes.md', text: 'nothing relevant here' },
  ];
  it('finds a WEAVE ID with verbatim context', () => {
    const r = lookupQuote(srcs, 'K12');
    expect(r).toContain('WEAVE.md');
    expect(r).toContain('two sheaves');
  });
  it('strips a WEAVE prefix when matching', () => {
    expect(lookupQuote(srcs, 'WEAVE K12')).toContain('two sheaves');
  });
  it('says what to do when missing', () => {
    const r = lookupQuote(srcs, 'K99');
    expect(r).toContain('Not found');
    expect(r).toContain('K99');
  });
  it('rejects empty queries', () => {
    expect(lookupQuote(srcs, '  ')).toContain('Empty');
  });
});

describe('lookupClip', () => {
  const okGet: ClipFetch = async (path) => {
    if (path.startsWith('meta')) return { ok: true, status: 200, body: JSON.stringify({ title: 'T', duration: 65, uploader: 'U' }) };
    return { ok: true, status: 200, body: JSON.stringify({ segments: [{ t: 4, d: 2, x: 'hello' }, { t: 70, d: 2, x: 'world' }] }) };
  };
  it('returns meta + timestamped transcript head', async () => {
    const r = await lookupClip('https://www.youtube.com/watch?v=abcDEF1234', okGet);
    expect(r).toContain('Title: T');
    expect(r).toContain('[0:04] hello');
    expect(r).toContain('[1:10] world');
  });
  it('accepts bare IDs and shorts URLs', async () => {
    expect(await lookupClip('abcDEF1234', okGet)).toContain('Title: T');
    expect(await lookupClip('https://youtu.be/abcDEF1234', okGet)).toContain('Title: T');
  });
  it('asks for an ID instead of inventing', async () => {
    expect(await lookupClip('find me something about rebirth', okGet)).toContain('paste IDs');
  });
  it('reports bridge-offline honestly', async () => {
    const r = await lookupClip('abcDEF1234', async () => ({ ok: false, status: 501, body: '{}' }));
    expect(r).toContain('offline');
  });
  it('reports youtube-blocked honestly', async () => {
    const r = await lookupClip('abcDEF1234', async () => ({ ok: false, status: 502, body: JSON.stringify({ error: 'youtube-blocked', hint: 'get cookies' }) }));
    expect(r).toContain('blocked');
    expect(r).toContain('get cookies');
  });
});

describe('runBoardcheck', () => {
  const MD = '| # | t | Beat |\n|---|---|---|\n| B1 | 0:00–0:45 | scene |\n| B2 | 0:45–1:30 | beat |\n';
  const manifest = { packs: [{ slug: 'film-x', manuscripts: [{ file: 'MOVIE.md' }] }] };
  const done = { status: 'done', result: { shots: 2, total_seconds: 90, by_act: { '': 90 }, warnings: ['B2: no parseable duration'], fits: true, over_seconds: 0 } };
  const get = async (path: string) => {
    if (path === '/packs/packs.json') return { ok: true, status: 200, body: JSON.stringify(manifest) };
    if (path === '/packs/film-x/manuscripts/MOVIE.md') return { ok: true, status: 200, body: MD };
    if (path.startsWith('/api/render/status')) return { ok: true, status: 200, body: JSON.stringify(done) };
    return { ok: false, status: 404, body: '' };
  };
  const post = async () => ({ ok: true, status: 200, body: JSON.stringify({ job_id: 'abc123', status: 'queued' }) });
  it('validates a pack storyboard end to end', async () => {
    const r = await runBoardcheck('film-x', get, post, 0, 3);
    expect(r).toContain('2 shots');
    expect(r).toContain('1:30 total');
    expect(r).toContain('Fits the 30:00 budget');
    expect(r).toContain('untimed rows');
  });
  it('asks for a slug when empty', async () => {
    expect(await runBoardcheck('  ', get, post, 0, 1)).toContain('Give a pack slug');
  });
  it('reports unknown packs', async () => {
    expect(await runBoardcheck('nope', get, post, 0, 1)).toContain('unknown pack');
  });
  it('reports bridge-offline honestly', async () => {
    const r = await runBoardcheck('film-x', get, async () => ({ ok: false, status: 501, body: '{}' }), 0, 1);
    expect(r).toContain('offline');
  });
  it('times out honestly on a stuck job', async () => {
    const stuck = async (path: string) => {
      if (path.startsWith('/api/render/status')) return { ok: true, status: 200, body: JSON.stringify({ status: 'running' }) };
      return get(path);
    };
    const r = await runBoardcheck('film-x', stuck, post, 0, 2);
    expect(r).toContain('still running');
  });
});
