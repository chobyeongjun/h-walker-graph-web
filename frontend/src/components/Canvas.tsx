import { useState } from 'react';
import { usePage } from '../store/page';
import DatasetPanel from './DatasetPanel';
import Cell from './cells/Cell';
import { PlayCircle, FileText, GitCompare } from 'lucide-react';
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
import type { Cell as CellModel } from '../store/page';

export default function Canvas() {
  const allCells = usePage((s) => s.cells);
  const activeRoomId = usePage((s) => s.activeRoomId);
  const rooms = usePage((s) => s.rooms);
  const setActiveRoom = usePage((s) => s.setActiveRoom);
  const activeRoom = rooms.find((r) => r.id === activeRoomId) ?? null;
  // In a room: show only that room's cells. In 거실: show all cells.
  const cells = activeRoomId && activeRoom
    ? allCells.filter((c) => activeRoom.cellIds.includes(c.id))
    : allCells;
  const pageTitle = usePage((s) => s.pageTitle);
  const setPageTitle = usePage((s) => s.setPageTitle);
  const runAll = usePage((s) => s.runAll);
  const runAllBusy = usePage((s) => s.runAllBusy);
  const reorderCells = usePage((s) => s.reorderCells);
  const globalPreset = usePage((s) => s.globalPreset);
  const pageTitleState = usePage((s) => s.pageTitle);
  const showToast = usePage((s) => s.showToast);
  const logHistory = usePage((s) => s.logHistory);
  const compareDatasets = usePage((s) => s.compareDatasets);
  const datasets = usePage((s) => s.datasets);
  const [paperBusy, setPaperBusy] = useState(false);
  const [compareBusy, setCompareBusy] = useState(false);

  async function runCompare() {
    if (compareBusy) return;
    setCompareBusy(true);
    try {
      await compareDatasets();
    } finally {
      setCompareBusy(false);
    }
  }

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
      const result = await paperBundle({
        preset: globalPreset,
        variant: 'col2',
        format: 'pdf',
        paper_title: pageTitleState,
        cells: paperCells,
      });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(result.blob);
      a.download = `hwalker_paper_${globalPreset}_${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);

      if (result.errorCount > 0) {
        // Loud warning — some cells were dropped. Also log the first one
        // so the user knows which cell to inspect first.
        logHistory({
          kind: 'tool', actor: 'you',
          label: `⚠ Paper bundle exported with ${result.errorCount} error(s) · ${globalPreset.toUpperCase()}`,
          meta: { first_error: result.firstError || '' },
        });
        showToast(
          `⚠ ${result.errorCount} cell(s) failed — ${result.firstError || 'see ERRORS.txt in the ZIP'}`,
        );
      } else {
        logHistory({
          kind: 'tool', actor: 'you',
          label: `Exported paper bundle · ${paperCells.length} cells · ${globalPreset.toUpperCase()}`,
        });
        showToast(`Paper bundle exported (${paperCells.length} cells)`);
      }
    } catch (e) {
      showToast(`Paper export failed: ${(e as Error).message}`);
    } finally {
      setPaperBusy(false);
    }
  }

  // Drag-and-drop reorder uses indices into the *visible* cells
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
          <a
            style={{ cursor: 'pointer', color: activeRoomId ? '#94A3B8' : '#F09708' }}
            onClick={() => setActiveRoom(null)}
            title="거실 — global view of all cells"
          >거실</a>
          {activeRoom && (
            <>
              <span>/</span>
              <a style={{ color: '#F09708' }}>{activeRoom.name}</a>
            </>
          )}
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
            onClick={runCompare}
            disabled={compareBusy || datasets.length < 2}
            title={datasets.length < 2
              ? 'Upload ≥ 2 datasets to compare them in one figure + cross-file stats'
              : 'Overlay all datasets in one figure + auto cross-file stats when conditions are tagged'}
            style={{
              marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6,
              background: 'rgba(167,139,250,.1)',
              borderColor: 'rgba(167,139,250,.45)',
              color: '#A78BFA', fontWeight: 600,
            }}
          >
            <GitCompare size={13} />
            {compareBusy ? 'Comparing…' : `RUN COMPARE${datasets.length >= 2 ? ` (${datasets.length})` : ''}`}
          </button>
          <button
            className="ds-btn"
            onClick={() => runAll()}
            disabled={runAllBusy || bindableCount === 0}
            title="Re-run analysis, compute, and graph rendering for all bound cells"
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
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
