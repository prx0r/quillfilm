import { beforeEach, describe, expect, it } from 'vitest';
import { useCanvasStore } from './useCanvasStore';

describe('canvas spatial editing', () => {
  beforeEach(() => useCanvasStore.setState({ blocks: [], selected: [], packSlug: '', open: false }));
  it('applyPositions moves blocks in world coords', async () => {
    useCanvasStore.getState().addBlock(10, 20);
    const id = useCanvasStore.getState().blocks[0].id;
    useCanvasStore.getState().applyPositions([{ id, x: 400, y: 300 }]);
    const b = useCanvasStore.getState().blocks[0];
    expect(b.x).toBe(400);
    expect(b.y).toBe(300);
  });
  it('applyPositions(persist=false) skips storage write but updates state', async () => {
    useCanvasStore.getState().addBlock(0, 0);
    const id = useCanvasStore.getState().blocks[0].id;
    useCanvasStore.getState().applyPositions([{ id, x: 99, y: 99 }], false);
    expect(useCanvasStore.getState().blocks[0].x).toBe(99);
  });
  it('shift-select toggles additively; plain toggles single', () => {
    useCanvasStore.getState().toggleSelect('a', true);
    useCanvasStore.getState().toggleSelect('b', true);
    expect(useCanvasStore.getState().selected).toEqual(['a', 'b']);
    useCanvasStore.getState().toggleSelect('b', true); // unselect
    expect(useCanvasStore.getState().selected).toEqual(['a']);
    useCanvasStore.getState().toggleSelect('c', false); // plain: sole select
    expect(useCanvasStore.getState().selected).toEqual(['c']);
  });
  it('clearSelection empties; removeBlock drops from selection', () => {
    useCanvasStore.getState().toggleSelect('a', true);
    useCanvasStore.getState().clearSelection();
    expect(useCanvasStore.getState().selected).toEqual([]);
    useCanvasStore.getState().addBlock(0, 0);
    const id = useCanvasStore.getState().blocks[0].id;
    useCanvasStore.getState().toggleSelect(id, true);
    useCanvasStore.getState().removeBlock(id);
    expect(useCanvasStore.getState().selected).toEqual([]);
  });
});
