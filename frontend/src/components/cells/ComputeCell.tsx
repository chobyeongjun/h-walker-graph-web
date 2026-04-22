import type { Cell } from '../../store/workspace';
import { useWorkspace } from '../../store/workspace';
import { COMPUTE_METRICS } from '../../data/computeMetrics';

interface Props { cell: Cell; }

export default function ComputeCell({ cell }: Props) {
  const update = useWorkspace((s) => s.updateCell);
  const showToast = useWorkspace((s) => s.showToast);
  const metric = COMPUTE_METRICS[cell.metric || 'per_stride'];

  if (!metric) {
    return <div className="cpt-wrap"><div className="cpt-sum"><em>Unknown metric</em></div></div>;
  }

  return (
    <>
      <div className="cpt-bar">
        <span className="cpt-chip">{cell.metric || 'per_stride'}</span>
        <select
          className="gt-sel"
          value={cell.metric || 'per_stride'}
          onChange={(e) => update(cell.id, { metric: e.target.value })}
          style={{ marginLeft: 8 }}
        >
          {Object.entries(COMPUTE_METRICS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <span style={{ color: '#9CA3AF' }}>{metric.label}</span>
        <span className="rest">
          <button onClick={() => showToast('CSV export: Phase B')}>CSV</button>
          <button onClick={() => showToast('Recompute: Phase B')}>Recompute</button>
        </span>
      </div>

      <div className="cpt-wrap">
        <div className="cpt-table">
          <table>
            <thead>
              <tr>{metric.cols.map((c, i) => <th key={i}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {metric.rows.map((row, i) => (
                <tr key={i}>{row.map((cell, j) => <td key={j}>{cell}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="cpt-sum">
          <h5>Summary</h5>
          {metric.summary.mean.map((v, i) => (
            <div key={i} className="row">
              <span>{metric.cols[i + 1] || 'metric'}</span><b>{v}</b>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
