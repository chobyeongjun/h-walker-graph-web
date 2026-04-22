import { useWorkspace } from '../store/workspace';
import DatasetPanel from './DatasetPanel';
import Cell from './cells/Cell';

export default function Canvas() {
  const cells = useWorkspace((s) => s.cells);
  const pageTitle = useWorkspace((s) => s.pageTitle);
  const setPageTitle = useWorkspace((s) => s.setPageTitle);

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
          <span>Last edit <b>2m ago</b></span>
          <span className="accent">{useWorkspace.getState().mode === 'pub' ? 'PUBLICATION MODE' : 'QUICK MODE'}</span>
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
