import { useState } from 'react';
import { useWorkspace } from '../store/workspace';
import DatasetPanel from './DatasetPanel';
import Cell from './cells/Cell';
import { PlayCircle, FileText } from 'lucide-react';
import { paperBundle } from '../api';
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
  const pageTitleState = useWorkspace((s) => s.pageTitle);
  const showToast = useWorkspace((s) => s.showToast);
  const logHistory = useWorkspace((s) => s.logHistory);
  const [paperBusy, setPaperBusy] = useState(false);

  async function runPaper() {
    if (paperBusy) return;
    setPaperBusy(true);
    try {
      const paperCells = cells
        .filter((c) => c.type !== 'llm')
        .map((c) => ({
          id: c.id,
          type: c.type as 'graph' | 'stat' | 'compute',
          title: c.title,
          graph: c.graph,
          stride_avg: c.strideAvg,
          dataset_id: c.dsIds[0],
          datasets: c.series && c.series.length >= 2
            ? c.series.map((s) => ({ id: s.dsId, label: s.label, color: s.color }))
            : undefined,
          op: c.op,
          a_col: c.inputs?.a,
          b_col: c.inputs?.b,
          datasets_a: c.statDatasetsA,
          datasets_b: c.statDatasetsB,
          metric: c.metric,
        }));
      const blob = await paperBundle({
        preset: globalPreset,
        variant: 'col2',
        format: 'pdf',
        paper_title: pageTitleState,
        cells: paperCells,
      });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `hwalker_paper_${globalPreset}_${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      logHistory({ kind: 'tool', actor: 'you',
        label: `Exported paper bundle · ${paperCells.length} cells · ${globalPreset.toUpperCase()}` });
      showToast(`Paper bundle exported (${paperCells.length} cells)`);
    } catch (e) {
      showToast(`Paper export failed: ${(e as Error).message}`);
    } finally {
      setPaperBusy(false);
    }
  }

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
          <button
            className="ds-btn"
            onClick={runPaper}
            disabled={paperBusy || cells.filter((c) => c.type !== 'llm').length === 0}
            title="Export a ZIP with figures (PDF+SVG) + stats tables + captions.txt + main.tex skeleton"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: '#F09708', color: '#0B0E2E',
              borderColor: '#F09708', fontWeight: 700,
            }}
          >
            <FileText size={13} />
            {paperBusy ? 'Packaging…' : 'RUN PAPER'}
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
