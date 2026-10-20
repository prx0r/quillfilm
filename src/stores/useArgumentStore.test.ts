import { describe, expect, it } from 'vitest';
import { childrenOf, rootsOf, type ArgGraph } from './useArgumentStore';

const G: ArgGraph = {
  name: 'karma-domino',
  collapsed: [],
  nodes: [
    { id: 'q1', kind: 'question', text: 'Is everything governed by karma?' },
    { id: 'a1', kind: 'claim', text: 'No — bile, seasons, assault too.' },
    { id: 'e1', kind: 'quote', text: 'Slip past what they themselves know.' },
    { id: 'g1', kind: 'gap', text: 'Who exactly then?' },
    { id: 'q2', kind: 'question', text: 'So what IS karma?' },
  ],
  edges: [
    { from: 'a1', to: 'q1', rel: 'answers' },
    { from: 'e1', to: 'a1', rel: 'supports' },
    { from: 'a1', to: 'g1', rel: 'leaves-open' },
    { from: 'q1', to: 'q2', rel: 'follows' },
  ],
};

describe('argument graph traversal', () => {
  it('roots are nodes with no incoming edges', () => {
    expect(rootsOf(G).map(n => n.id)).toEqual(['q1']);
  });
  it('children follow answers/supports/resolves/leaves-open + follows', () => {
    expect(childrenOf(G, 'q1').map(n => n.id)).toEqual(['q2', 'a1']);
    expect(childrenOf(G, 'a1').map(n => n.id)).toEqual(['e1', 'g1']);
    expect(childrenOf(G, 'e1')).toEqual([]);
  });
  it('orders kinds deterministically: question, claim, resolution, quote, gap', () => {
    const kids = childrenOf(G, 'q1');
    expect(kids[0].kind).toBe('question');
  });
});

describe('toggle', () => {
  it('collapses and expands a node', async () => {
    const { useArgumentStore } = await import('./useArgumentStore');
    useArgumentStore.setState({ graphs: [{ name: 'g', collapsed: [], nodes: [
      { id: 'q1', kind: 'question', text: 'Q?' },
    ], edges: [] }] });
    useArgumentStore.getState().toggle(0, 'q1');
    expect(useArgumentStore.getState().graphs[0].collapsed).toEqual(['q1']);
    useArgumentStore.getState().toggle(0, 'q1');
    expect(useArgumentStore.getState().graphs[0].collapsed).toEqual([]);
  });
});
