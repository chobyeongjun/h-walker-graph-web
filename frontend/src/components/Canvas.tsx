import { useWorkspace } from '../store/workspace';
import DatasetPanel from './DatasetPanel';
import Cell from './cells/Cell';
import { PlayCircle } from 'lucide-react';

export default function Canvas() {
  const cells = useWorkspace((s) => s.cells);
  const pageTitle = useWorkspace((s) => s.pageTitle);
  const setPageTitle = useWorkspace((s) => s.setPageTitle);
  const runAll = useWorkspace((s) => s.runAll);
  const runAllBusy = useWorkspace((s) => s.runAllBusy);
  const mode = useWorkspace((s) => s.mode);

  const liveCount = cells.filter((c) =>
    (c.type === 'graph' && c.previewBlobUrl) ||
    (c.type === 'compute' && c.computeData) ||
    (c.type === 'stat' && c.statData)
  ).length;
  const bindableCount = cells.filter((c) => c.type !== 'llm' && c.dsIds[0]).length;

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
          <span className="accent">{mode === 'pub' ? 'PUBLICATION MODE' : 'QUICK MODE'}</span>
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

      <div className="cells">
        {cells.map((c, i) => (
          <Cell key={c.id} cell={c} index={i} />
        ))}
      </div>
    </section>
  );
}
