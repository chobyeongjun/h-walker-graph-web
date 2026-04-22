import { useMemo } from 'react';
import type { Cell } from '../../store/workspace';
import { useWorkspace } from '../../store/workspace';
import { STAT_OPS, type StatResult } from '../../data/statOps';
import type { StatsResponse } from '../../api';

interface Props { cell: Cell; }

const BACKEND_OPS = ['ttest_paired', 'ttest_welch', 'anova1', 'pearson', 'cohens_d', 'shapiro'];

export default function StatCell({ cell }: Props) {
  const update = useWorkspace((s) => s.updateCell);
  const runStat = useWorkspace((s) => s.runStat);
  const showToast = useWorkspace((s) => s.showToast);
  const hasDataset = !!cell.dsIds[0];
  const canRunBackend = hasDataset && BACKEND_OPS.includes(cell.op || '') && !!cell.inputs?.a;

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
          <label>Run</label>
          <div>
            <button
              className="on"
              onClick={() => runStat(cell.id)}
              disabled={!canRunBackend || !!cell.loading}
              style={{ opacity: canRunBackend ? 1 : 0.5 }}
            >
              {cell.loading ? '…running' : hasDataset ? '▸ Run on dataset' : '▸ Run (mock only)'}
            </button>
            {hasDataset && live && <span style={{ marginLeft: 8, color: '#00FFB2', fontSize: 10 }}>● live</span>}
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
