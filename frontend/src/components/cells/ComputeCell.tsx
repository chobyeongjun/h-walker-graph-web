import { useEffect } from 'react';
import type { Cell } from '../../store/page';
import { usePage } from '../../store/page';
import { COMPUTE_METRICS } from '../../data/computeMetrics';

interface Props { cell: Cell; }

export default function ComputeCell({ cell }: Props) {
  const update = usePage((s) => s.updateCell);
  const runCompute = usePage((s) => s.runCompute);
  const showToast = usePage((s) => s.showToast);
  const fallback = COMPUTE_METRICS[cell.metric || 'per_stride'];
  const hasDataset = !!cell.dsIds[0];
  const live = cell.computeData;

  // Auto-run on mount when bound to a dataset
  useEffect(() => {
    if (hasDataset && !live && !cell.loading && !cell.error) {
      runCompute(cell.id);
    }
  }, [hasDataset, live, cell.loading, cell.error, cell.id, runCompute]);

  // Re-run when metric changes
  useEffect(() => {
    if (!hasDataset) return;
    const h = setTimeout(() => { runCompute(cell.id); }, 120);
    return () => clearTimeout(h);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cell.metric]);

  const cols = live?.cols ?? fallback?.cols ?? [];
  const rows = live?.rows ?? fallback?.rows ?? [];
  const summary = live?.summary?.mean ?? fallback?.summary.mean ?? [];
  const label = live?.label ?? fallback?.label ?? cell.metric;

  function exportCsv() {
    if (!live) { showToast('No data yet'); return; }
    const lines = [cols.join(','), ...rows.map((r) => r.join(','))];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${cell.id}_${cell.metric}.csv`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  return (
    <>
      <div className="cpt-bar">
        <span className="cpt-chip">{cell.metric || 'per_stride'}</span>
        <select
          className="gt-sel"
          value={cell.metric || 'per_stride'}
          onChange={(e) => update(cell.id, { metric: e.target.value, computeData: undefined })}
          style={{ marginLeft: 8 }}
        >
          {Object.entries(COMPUTE_METRICS).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
        <span style={{ color: '#9CA3AF' }}>{label}</span>
        {hasDataset && live && <span style={{ color: '#00FFB2', fontSize: 10 }}>● live</span>}
        {!hasDataset && <span style={{ color: '#6B7280', fontSize: 10 }}>mock</span>}
        <span className="rest">
          <button onClick={exportCsv} disabled={!live}>CSV</button>
          <button
            onClick={() => runCompute(cell.id)}
            disabled={!hasDataset || !!cell.loading}
          >
            {cell.loading ? '…' : 'Recompute'}
          </button>
        </span>
      </div>

      {cell.error ? (
        <div className="cpt-wrap" style={{ padding: 16 }}>
          <div style={{ color: '#f87171', fontSize: 12 }}>
            <b>Compute failed</b> — {cell.error}
          </div>
          <button onClick={() => runCompute(cell.id)} style={{ marginTop: 8 }}>Retry</button>
        </div>
      ) : cell.loading && !live ? (
        <div className="cpt-wrap" style={{ padding: 16 }}>
          <div className="cpt-skeleton">
            <div className="ps-bar" /><div className="ps-bar" /><div className="ps-bar" /><div className="ps-bar" />
          </div>
          <div style={{ color: '#6B7280', fontSize: 10, marginTop: 8 }}>Computing…</div>
        </div>
      ) : (
        <div className="cpt-wrap">
          <div className="cpt-table">
            <table>
              <thead>
                <tr>{cols.map((c, i) => <th key={i}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i}>{row.map((cellV, j) => <td key={j}>{cellV}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="cpt-sum">
            <h5>Summary</h5>
            {summary.map((v, i) => (
              <div key={i} className="row">
                <span>{cols[i + 1] || 'metric'}</span><b>{v}</b>
              </div>
            ))}
            {live?.meta?.n_strides != null && (
              <div className="row" style={{ color: '#6B7280', fontSize: 10, marginTop: 6 }}>
                <span>strides</span><b>{String(live.meta.n_strides)}</b>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
