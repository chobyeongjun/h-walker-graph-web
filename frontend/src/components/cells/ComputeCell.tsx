import { useEffect, useState } from 'react';
import type { Cell } from '../../store/page';
import { usePage } from '../../store/page';
import { COMPUTE_METRICS } from '../../data/computeMetrics';
import { updateDatasetMeta } from '../../api';

interface Props { cell: Cell; }

const METRIC_GROUPS = [
  { label: 'Force / Kinetic',   keys: ['per_stride', 'impulse', 'loading_rate', 'target_dev'] },
  { label: 'Spatiotemporal',    keys: ['cadence', 'stride_length', 'stance_time', 'swing_time'] },
  { label: 'Kinematics',        keys: ['rom'] },
  { label: 'Summary / Fatigue', keys: ['fatigue_index', 'symmetry_summary'] },
];

export default function ComputeCell({ cell }: Props) {
  const update = usePage((s) => s.updateCell);
  const runCompute = usePage((s) => s.runCompute);
  const showToast = usePage((s) => s.showToast);
  const allDatasets = usePage((s) => s.datasets);
  const fallback = COMPUTE_METRICS[cell.metric || 'per_stride'];
  const hasDataset = !!cell.dsIds[0];
  const live = cell.computeData;
  const ds = allDatasets.find((d) => d.id === cell.dsIds[0]);
  const isStrideLen = cell.metric === 'stride_length';

  // Treadmill inline editor state
  const [beltInput, setBeltInput] = useState<string>(String(ds?.belt_speed_ms ?? ''));
  const [treadmillBusy, setTreadmillBusy] = useState(false);

  useEffect(() => {
    setBeltInput(String(ds?.belt_speed_ms ?? ''));
  }, [ds?.belt_speed_ms]);

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
  const warnings = Array.isArray(live?.meta?.warnings) ? (live!.meta.warnings as string[]) : [];

  async function saveTreadmill() {
    if (!ds) return;
    const speed = parseFloat(beltInput);
    if (isNaN(speed) || speed <= 0) { showToast('유효한 속도를 입력하세요 (m/s)'); return; }
    setTreadmillBusy(true);
    try {
      await updateDatasetMeta(ds.id, { is_treadmill: true, belt_speed_ms: speed });
      // Update store dataset manually (optimistic)
      usePage.setState((s) => ({
        datasets: s.datasets.map((d) =>
          d.id === ds.id ? { ...d, is_treadmill: true, belt_speed_ms: speed } : d,
        ),
      }));
      // Re-run with new speed
      runCompute(cell.id);
      showToast(`트레드밀 모드 설정: ${speed} m/s`);
    } catch {
      showToast('저장 실패');
    } finally {
      setTreadmillBusy(false);
    }
  }

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
          {METRIC_GROUPS.map((g) => (
            <optgroup key={g.label} label={g.label}>
              {g.keys.filter((k) => k in COMPUTE_METRICS).map((k) => (
                <option key={k} value={k}>{COMPUTE_METRICS[k].label}</option>
              ))}
            </optgroup>
          ))}
        </select>
        <span style={{ color: '#9CA3AF', fontSize: 10.5, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{label}</span>
        {hasDataset && live && <span style={{ color: '#00FFB2', fontSize: 10 }}>● live</span>}
        {!hasDataset && <span style={{ color: '#6B7280', fontSize: 10 }}>mock</span>}
        <span className="rest">
          <button onClick={exportCsv} disabled={!live}>CSV</button>
          <button onClick={() => runCompute(cell.id)} disabled={!hasDataset || !!cell.loading}>
            {cell.loading ? '…' : 'Recompute'}
          </button>
        </span>
      </div>

      {/* Stride length treadmill config — always shown when metric is stride_length.
          ZUPT (over-ground integration) gives garbage for treadmill data.
          The correct formula is: stride_time × belt_speed. */}
      {isStrideLen && hasDataset && (
        <div className="cpt-treadmill">
          <span className="cpt-treadmill-label">
            {ds?.is_treadmill
              ? `✓ 트레드밀 모드 · ${ds.belt_speed_ms ?? '?'} m/s`
              : '⚠ ZUPT는 트레드밀에서 정확하지 않음'}
          </span>
          <span style={{ color: '#6B7280', fontSize: 10 }}>벨트 속도</span>
          <input
            className="cpt-belt-input"
            type="number"
            step="0.05"
            min="0.1"
            max="3.0"
            placeholder="m/s"
            value={beltInput}
            onChange={(e) => setBeltInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') saveTreadmill(); }}
          />
          <button
            className="gt-btn"
            style={{ padding: '3px 10px', fontSize: 10.5 }}
            onClick={saveTreadmill}
            disabled={treadmillBusy}
          >
            {treadmillBusy ? '…' : '적용'}
          </button>
          {ds?.is_treadmill && (
            <button
              style={{ fontSize: 10, color: '#6B7280', background: 'none', border: 'none', cursor: 'pointer', padding: '2px 6px' }}
              onClick={async () => {
                await updateDatasetMeta(ds.id, { is_treadmill: false, belt_speed_ms: null });
                usePage.setState((s) => ({
                  datasets: s.datasets.map((d) =>
                    d.id === ds.id ? { ...d, is_treadmill: false, belt_speed_ms: null } : d,
                  ),
                }));
                runCompute(cell.id);
              }}
            >ZUPT로</button>
          )}
        </div>
      )}

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
                  <tr key={i} className={row[0] === '…' ? 'ellipsis' : ''}>
                    {row.map((cellV, j) => <td key={j}>{cellV}</td>)}
                  </tr>
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
            {live?.meta?.mode && (
              <div className="row" style={{
                color: live.meta.mode === 'treadmill' ? '#00FFB2' : '#6B7280',
                fontSize: 10, marginTop: 4,
              }}>
                <span>mode</span><b>{String(live.meta.mode)}</b>
              </div>
            )}
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="cpt-warnings">
          <b>⚠ 데이터 품질 경고</b>
          {warnings.map((w, i) => <div key={i}>· {w}</div>)}
        </div>
      )}
    </>
  );
}
