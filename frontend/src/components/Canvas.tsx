import { useWorkspace } from '../store/workspace';
import DatasetPanel from './DatasetPanel';
import Cell from './cells/Cell';
import { PlayCircle } from 'lucide-react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { Cell as CellModel } from '../store/workspace';

export default function Canvas() {
  const cells = useWorkspace((s) => s.cells);
  const pageTitle = useWorkspace((s) => s.pageTitle);
  const setPageTitle = useWorkspace((s) => s.setPageTitle);
  const runAll = useWorkspace((s) => s.runAll);
  const runAllBusy = useWorkspace((s) => s.runAllBusy);
  const reorderCells = useWorkspace((s) => s.reorderCells);
  const globalPreset = useWorkspace((s) => s.globalPreset);

  const workCells = cells.filter((c) => c.type !== 'llm');
  const liveCount = workCells.filter((c) =>
    (c.type === 'graph' && c.previewBlobUrl) ||
    (c.type === 'compute' && c.computeData) ||
    (c.type === 'stat' && c.statData)
  ).length;
  const bindableCount = workCells.filter((c) => c.dsIds[0]).length;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    // Indices reference `cells` (including llm cells), so map back through
    const fromIdx = cells.findIndex((c) => c.id === active.id);
    const toIdx = cells.findIndex((c) => c.id === over.id);
    if (fromIdx < 0 || toIdx < 0) return;
    reorderCells(fromIdx, toIdx);
  }

  return (
    <section className="canvas">
      <div className="page-head">
        <div className="page-crumbs">
          <a>Project</a><span>/</span>
          <a>Treadmill · 0.8 m/s</a><span>/</span>
          <a>Pilot 03</a>
        </div>
        <div
          className="page-title"
          contentEditable
          suppressContentEditableWarning
          onBlur={(e) => setPageTitle(e.currentTarget.textContent || '')}
        >{pageTitle}</div>
        <div className="page-meta">
          <span><b>{cells.length}</b> cells</span>
          <span><b>{liveCount}</b> / {bindableCount} live</span>
          <span className="accent">{globalPreset.toUpperCase()}</span>
          <button
            className="ds-btn"
            onClick={() => runAll()}
            disabled={runAllBusy || bindableCount === 0}
            title="Re-run analysis, compute, and graph rendering for all bound cells"
            style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            <PlayCircle size={13} />
            {runAllBusy ? 'Running…' : 'RUN ALL'}
          </button>
        </div>
      </div>

      <DatasetPanel />

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext
          items={workCells.map((c) => c.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="cells">
            {workCells.map((c, i) => (
              <SortableCell key={c.id} cell={c} index={i} />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </section>
  );
}

function SortableCell({ cell, index }: { cell: CellModel; index: number }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: cell.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 100 : 'auto' as const,
    opacity: isDragging ? 0.85 : 1,
  };
  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <Cell cell={cell} index={index} dragHandle={listeners} />
    </div>
  );
}
