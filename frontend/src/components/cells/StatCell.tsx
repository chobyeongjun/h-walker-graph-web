import { useMemo } from 'react';
import type { Cell } from '../../store/workspace';
import { useWorkspace } from '../../store/workspace';
import { STAT_OPS, type StatResult } from '../../data/statOps';

interface Props { cell: Cell; }

export default function StatCell({ cell }: Props) {
  const update = useWorkspace((s) => s.updateCell);
  const showToast = useWorkspace((s) => s.showToast);
  const op = STAT_OPS[cell.op || 'ttest_paired'];
  const result = useMemo(() => op.run(cell.inputs || { a: '', b: '' }), [op, cell.inputs]);

  const apaText = formatReport(result, cell.fmt || 'apa');

  return (
    <div className="stat-body">
      <div className="stat-inputs">
        <div className="stat-row">
          <label>OP</label>
          <div className="op">
            {Object.entries(STAT_OPS).map(([k, v]) => (
              <button key={k}
                className={cell.op === k ? 'on' : ''}
                onClick={() => update(cell.id, { op: k })}
              >{v.label}</button>
            ))}
          </div>
        </div>
        <div className="stat-row">
          <label>Input A</label>
          <input
            type="text"
            value={cell.inputs?.a || ''}
            onChange={(e) => update(cell.id, { inputs: { a: e.target.value, b: cell.inputs?.b || '' } })}
            placeholder="c2.L_peak"
          />
        </div>
        <div className="stat-row">
          <label>Input B</label>
          <input
            type="text"
            value={cell.inputs?.b || ''}
            onChange={(e) => update(cell.id, { inputs: { a: cell.inputs?.a || '', b: e.target.value } })}
            placeholder="c2.R_peak"
          />
        </div>
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
      </div>

      <div className="stat-output">
        <StatKV r={result} />
        <div className="stat-apa">
          <button className="copy" onClick={() => {
            navigator.clipboard.writeText(apaText.replace(/<[^>]+>/g, ''));
            showToast('Copied');
          }}>COPY</button>
          <span dangerouslySetInnerHTML={{ __html: apaText }} />
        </div>
      </div>
    </div>
  );
}

function StatKV({ r }: { r: StatResult }) {
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

function formatReport(r: StatResult, fmt: string): string {
  if (fmt === 'apa') {
    if (r.t) return `<b>${r.test}</b>: <b>t</b>(${r.df}) = ${r.t}, <b>p</b> = ${r.p}, <b>d</b> = ${r.cohen_d || '–'}.`;
    if (r.F) return `<b>${r.test}</b>: <b>F</b>(${r.df1},${r.df2}) = ${r.F}, <b>p</b> = ${r.p}, <b>η²</b> = ${r.eta2 || '–'}.`;
    if (r.r) return `<b>${r.test}</b>: <b>r</b> = ${r.r}, <b>p</b> = ${r.p}, 95% CI ${r.ci95}.`;
    return r.test;
  }
  if (fmt === 'ieee') return `${r.test}; t=${r.t ?? r.F ?? r.r}, p=${r.p}`;
  return `test,stat,p\n${r.test},${r.t ?? r.F ?? r.r},${r.p}`;
}
