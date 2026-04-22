import { useEffect, useMemo, useState } from 'react';
import type { Cell } from '../../store/workspace';
import { useWorkspace } from '../../store/workspace';
import { STAT_OPS, type StatResult } from '../../data/statOps';
import { listStatMetrics, type StatsResponse, type MetricDescriptor } from '../../api';

interface Props { cell: Cell; }

const BACKEND_OPS = ['ttest_paired', 'ttest_welch', 'anova1', 'pearson', 'cohens_d', 'shapiro'];

export default function StatCell({ cell }: Props) {
  const update = useWorkspace((s) => s.updateCell);
  const runStat = useWorkspace((s) => s.runStat);
  const showToast = useWorkspace((s) => s.showToast);
  const allDatasets = useWorkspace((s) => s.datasets);
  const hasDataset = !!cell.dsIds[0];
  const crossFile = (cell.statDatasetsA?.length || 0) > 0 || (cell.statDatasetsB?.length || 0) > 0;
  const canRunBackend = crossFile
    ? BACKEND_OPS.includes(cell.op || '')
    : hasDataset && BACKEND_OPS.includes(cell.op || '') && !!cell.inputs?.a;

  const [metrics, setMetrics] = useState<MetricDescriptor[]>([]);
  useEffect(() => {
    listStatMetrics().then(setMetrics).catch(() => {});
  }, []);

  // Mock fallback (when no dataset, keeps demo working)
  const mockOp = STAT_OPS[cell.op || 'ttest_paired'];
  const mockResult = useMemo(
    () => (mockOp ? mockOp.run(cell.inputs || { a: '', b: '' }) : null),
    [mockOp, cell.inputs],
  );

  const live = cell.statData;
  const apaText = live ? formatBackendReport(live, cell.fmt || 'apa')
                  : mockResult ? formatMockReport(mockResult, cell.fmt || 'apa')
                  : '';

  return (
    <div className="stat-body">
      <div className="stat-inputs">
        <div className="stat-row">
          <label>OP</label>
          <div className="op">
            {BACKEND_OPS.map((k) => (
              <button
                key={k}
                className={cell.op === k ? 'on' : ''}
                onClick={() => update(cell.id, { op: k, statData: undefined })}
              >{prettyOp(k)}</button>
            ))}
          </div>
        </div>
        <div className="stat-row">
          <label>{hasDataset ? 'A column' : 'Input A'}</label>
          <input
            type="text"
            value={cell.inputs?.a || ''}
            onChange={(e) => update(cell.id, {
              inputs: { a: e.target.value, b: cell.inputs?.b || '' },
              statData: undefined,
            })}
            placeholder={hasDataset ? 'L_ActForce_N' : 'c2.L_peak'}
          />
        </div>
        {cell.op !== 'shapiro' && cell.op !== 'anova1' && (
          <div className="stat-row">
            <label>{hasDataset ? 'B column' : 'Input B'}</label>
            <input
              type="text"
              value={cell.inputs?.b || ''}
              onChange={(e) => update(cell.id, {
                inputs: { a: cell.inputs?.a || '', b: e.target.value },
                statData: undefined,
              })}
              placeholder={hasDataset ? 'R_ActForce_N' : 'c2.R_peak'}
            />
          </div>
        )}
        <div className="stat-row">
          <label>Format</label>
          <div className="stat-fmt">
            {(['apa', 'ieee', 'csv'] as const).map((f) => (
              <button key={f}
                className={cell.fmt === f ? 'on' : ''}
                onClick={() => update(cell.id, { fmt: f })}
              >{f}</button>
            ))}
          </div>
        </div>
        <div className="stat-row">
          <label>Mode</label>
          <div className="op" style={{ flexWrap: 'wrap', gap: 4 }}>
            <button
              className={!crossFile ? 'on' : ''}
              onClick={() => update(cell.id, {
                statDatasetsA: undefined, statDatasetsB: undefined,
                statData: undefined,
              })}
            >Single · columns</button>
            <button
              className={crossFile ? 'on' : ''}
              onClick={() => {
                if (!allDatasets.length) { showToast('Upload datasets first'); return; }
                const defaultMetric = cell.statMetric || 'peak_force_L';
                // If no cross-file already set, group by 'condition' field if available,
                // else split datasets in half as a rough placeholder.
                const withCond = allDatasets.filter((d) => !!d.condition);
                if (withCond.length >= 2) {
                  const conds = [...new Set(withCond.map((d) => d.condition))];
                  const A = withCond.filter((d) => d.condition === conds[0]);
                  const B = withCond.filter((d) => d.condition === conds[1]);
                  update(cell.id, {
                    statDatasetsA: A.map((d) => ({ id: d.id, metric: defaultMetric })),
                    statDatasetsB: B.map((d) => ({ id: d.id, metric: defaultMetric })),
                    statMetric: defaultMetric,
                    statData: undefined,
                  });
                } else {
                  const mid = Math.ceil(allDatasets.length / 2);
                  update(cell.id, {
                    statDatasetsA: allDatasets.slice(0, mid).map((d) => ({ id: d.id, metric: defaultMetric })),
                    statDatasetsB: allDatasets.slice(mid).map((d) => ({ id: d.id, metric: defaultMetric })),
                    statMetric: defaultMetric,
                    statData: undefined,
                  });
                }
              }}
            >Cross-file · groups</button>
          </div>
        </div>

        {crossFile && (
          <>
            <div className="stat-row">
              <label>Metric</label>
              <select
                className="gt-sel"
                value={cell.statMetric || 'peak_force_L'}
                onChange={(e) => {
                  const m = e.target.value;
                  update(cell.id, {
                    statMetric: m,
                    statDatasetsA: (cell.statDatasetsA || []).map((r) => ({ ...r, metric: m })),
                    statDatasetsB: (cell.statDatasetsB || []).map((r) => ({ ...r, metric: m })),
                    statData: undefined,
                  });
                }}
              >
                {metrics.length === 0 && <option>loading…</option>}
                {metrics.map((m) => (
                  <option key={m.key} value={m.key}>
                    {m.label} [{m.unit}]
                  </option>
                ))}
              </select>
            </div>
            <div className="stat-row">
              <label>Group A</label>
              <DatasetGroupEditor
                refs={cell.statDatasetsA || []}
                metric={cell.statMetric || 'peak_force_L'}
                onChange={(refs) => update(cell.id, { statDatasetsA: refs, statData: undefined })}
                datasets={allDatasets}
              />
            </div>
            {cell.op !== 'shapiro' && cell.op !== 'anova1' && (
              <div className="stat-row">
                <label>Group B</label>
                <DatasetGroupEditor
                  refs={cell.statDatasetsB || []}
                  metric={cell.statMetric || 'peak_force_L'}
                  onChange={(refs) => update(cell.id, { statDatasetsB: refs, statData: undefined })}
                  datasets={allDatasets}
                />
              </div>
            )}
          </>
        )}

        <div className="stat-row">
          <label>Run</label>
          <div>
            <button
              className="on"
              onClick={() => runStat(cell.id)}
              disabled={!canRunBackend || !!cell.loading}
              style={{ opacity: canRunBackend ? 1 : 0.5 }}
            >
              {cell.loading ? '…running' :
                crossFile ? '▸ Run cross-file stats' :
                hasDataset ? '▸ Run on dataset' : '▸ Run (mock only)'}
            </button>
            {(hasDataset || crossFile) && live && <span style={{ marginLeft: 8, color: '#00FFB2', fontSize: 10 }}>● live</span>}
          </div>
        </div>
      </div>

      <div className="stat-output">
        {cell.error && (
          <div className="stat-val" style={{ color: '#f87171' }}>
            <span>Error</span><b>{cell.error}</b>
          </div>
        )}
        {live ? <BackendKV r={live} /> : mockResult ? <MockKV r={mockResult} /> : null}
        {apaText && (
          <div className="stat-apa">
            <button className="copy" onClick={() => {
              navigator.clipboard.writeText(apaText.replace(/<[^>]+>/g, ''));
              showToast('Copied');
            }}>COPY</button>
            <span dangerouslySetInnerHTML={{ __html: apaText }} />
          </div>
        )}
      </div>
    </div>
  );
}

function prettyOp(k: string): string {
  const map: Record<string, string> = {
    ttest_paired: 'paired t',
    ttest_welch: 'Welch t',
    anova1: 'ANOVA',
    pearson: 'Pearson r',
    cohens_d: "Cohen's d",
    shapiro: 'Shapiro',
  };
  return map[k] || k;
}

function BackendKV({ r }: { r: StatsResponse }) {
  const entries: Array<[string, string, boolean?]> = [
    ['Test', r.name, false],
    ['n', Array.isArray(r.n) ? r.n.join(' / ') : String(r.n), false],
    [r.stat_name, r.stat.toFixed(r.stat_name === 'r' || r.stat_name === 'ρ' || r.stat_name === 'd' ? 3 : 2), false],
    ['df', Array.isArray(r.df) ? `${r.df[0]}, ${r.df[1]}` : r.df != null ? Number(r.df).toFixed(1) : '', false],
    ['p', r.p == null ? '' : (r.p < 0.001 ? '<0.001' : r.p.toFixed(3)), !!(r.p != null && r.p < 0.05)],
    ['effect', r.effect_size ? `${r.effect_size.name} = ${r.effect_size.value.toFixed(3)}${r.effect_size.label ? ` (${r.effect_size.label})` : ''}` : '', false],
    ['95% CI', r.ci95 ? `[${r.ci95[0].toFixed(2)}, ${r.ci95[1].toFixed(2)}]` : '', false],
    ['assumption', r.assumption ? `${r.assumption.name}: p=${r.assumption.p.toFixed(3)} ${r.assumption.passed ? '✓' : '✗'}` : '', false],
    ['fallback', r.fallback_used ? 'non-parametric (Shapiro failed)' : '', false],
  ].filter((e) => e[1]) as Array<[string, string, boolean?]>;

  return (
    <>
      {entries.map(([k, v, sig], i) => (
        <div key={i} className={`stat-val${sig ? ' sig' : ''}`}>
          <span>{k}</span><b>{v}</b>
        </div>
      ))}
    </>
  );
}

function formatBackendReport(r: StatsResponse, fmt: string): string {
  const p = r.p == null ? '–' : r.p < 0.001 ? '<0.001' : r.p.toFixed(3);
  const d = r.df == null ? '' : Array.isArray(r.df) ? `(${r.df[0]},${r.df[1]})` : `(${Number(r.df).toFixed(1)})`;
  if (fmt === 'apa') {
    return `<b>${r.name}</b>: <b>${r.stat_name}</b>${d} = ${r.stat.toFixed(2)}, <b>p</b> = ${p}`
      + (r.effect_size ? `, <b>${r.effect_size.name}</b> = ${r.effect_size.value.toFixed(3)}` : '')
      + '.';
  }
  if (fmt === 'ieee') {
    return `${r.name}; ${r.stat_name}${d}=${r.stat.toFixed(2)}, p=${p}`;
  }
  return `test,stat,df,p\n${r.name},${r.stat},${r.df},${r.p}`;
}

function MockKV({ r }: { r: StatResult }) {
  const raw: Array<[string, string, boolean?]> = [
    ['Test', r.test, false],
    ['n', r.n !== undefined ? String(r.n) : '', false],
    ['stat',
      r.t !== undefined ? String(r.t)
      : r.F !== undefined ? String(r.F)
      : r.r !== undefined ? String(r.r)
      : '', false],
    ['df', r.df !== undefined ? String(r.df) : '', false],
    ['p', r.p, r.psig],
    ['mean Δ', r.mean_diff || '', false],
    ['95% CI', r.ci95 || '', false],
    ['effect size',
      r.cohen_d !== undefined ? r.cohen_d
      : r.eta2 !== undefined ? r.eta2
      : '', false],
    ['Effect', r.effect || '', false],
  ];
  const entries = raw.filter((e) => e[1]);
  return (
    <>
      {entries.map(([k, v, sig], i) => (
        <div key={i} className={`stat-val${sig ? ' sig' : ''}`}>
          <span>{k}</span><b>{v}</b>
        </div>
      ))}
    </>
  );
}

function DatasetGroupEditor({ refs, metric, onChange, datasets }: {
  refs: Array<{ id: string; metric: string }>;
  metric: string;
  onChange: (refs: Array<{ id: string; metric: string }>) => void;
  datasets: Array<{ id: string; name: string; tag: string; condition?: string; subject_id?: string }>;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: 1 }}>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {refs.map((r) => {
          const d = datasets.find((x) => x.id === r.id);
          return (
            <span key={r.id} style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              padding: '3px 8px', background: 'rgba(240,151,8,.08)',
              border: '1px solid rgba(240,151,8,.3)', borderRadius: 5,
              fontSize: 11,
            }}>
              {d?.subject_id || d?.name || r.id}
              {d?.condition && <span style={{ color: '#A78BFA' }}>/{d.condition}</span>}
              <button
                onClick={() => onChange(refs.filter((x) => x.id !== r.id))}
                style={{
                  background: 'transparent', border: 'none', cursor: 'pointer',
                  color: '#f87171', padding: 0, fontSize: 12,
                }}
              >×</button>
            </span>
          );
        })}
      </div>
      <select
        className="gt-sel"
        value=""
        onChange={(e) => {
          if (e.target.value && !refs.some((r) => r.id === e.target.value)) {
            onChange([...refs, { id: e.target.value, metric }]);
          }
        }}
        style={{ maxWidth: 280 }}
      >
        <option value="">+ add dataset…</option>
        {datasets
          .filter((d) => !refs.some((r) => r.id === d.id))
          .map((d) => (
            <option key={d.id} value={d.id}>
              {d.subject_id ? `${d.subject_id} · ` : ''}{d.condition ? `[${d.condition}] ` : ''}{d.name}
            </option>
          ))}
      </select>
    </div>
  );
}

function formatMockReport(r: StatResult, fmt: string): string {
  if (fmt === 'apa') {
    if (r.t) return `<b>${r.test}</b>: <b>t</b>(${r.df}) = ${r.t}, <b>p</b> = ${r.p}, <b>d</b> = ${r.cohen_d || '–'}.`;
    if (r.F) return `<b>${r.test}</b>: <b>F</b>(${r.df1},${r.df2}) = ${r.F}, <b>p</b> = ${r.p}, <b>η²</b> = ${r.eta2 || '–'}.`;
    if (r.r) return `<b>${r.test}</b>: <b>r</b> = ${r.r}, <b>p</b> = ${r.p}, 95% CI ${r.ci95}.`;
    return r.test;
  }
  if (fmt === 'ieee') return `${r.test}; t=${r.t ?? r.F ?? r.r}, p=${r.p}`;
  return `test,stat,p\n${r.test},${r.t ?? r.F ?? r.r},${r.p}`;
}
