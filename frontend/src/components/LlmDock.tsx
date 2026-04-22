import { useState } from 'react';
import { Send } from 'lucide-react';
import { useWorkspace, type Cell } from '../store/workspace';
import { claudeComplete, type ToolUseBlock } from '../api';

export default function LlmDock() {
  const [q, setQ] = useState('');
  const datasets = useWorkspace((s) => s.datasets);
  const cells = useWorkspace((s) => s.cells);
  const addCell = useWorkspace((s) => s.addCell);
  const showToast = useWorkspace((s) => s.showToast);
  const active = datasets.find((d) => d.active);

  async function send() {
    const prompt = q.trim();
    if (!prompt) return;
    setQ('');
    const id = 'c' + Date.now();

    // Optimistic cell
    const optimistic: Cell = {
      id, type: 'llm', dsIds: active ? [active.id] : [],
      prompt,
      refs: cells.slice(-2).map((c) => c.id),
      answer: { text: ['<em>Thinking…</em>'] },
    };
    addCell(optimistic);

    try {
      const resp = await claudeComplete({
        prompt,
        context: {
          cells: cells.map((c) => ({ id: c.id, type: c.type, graph: c.graph, op: c.op, metric: c.metric })),
          active_dataset_id: active?.id ?? null,
        },
      });

      const txt = (resp.reply || '').trim();
      const dispatched: string[] = [];
      if (resp.tool_uses && resp.tool_uses.length) {
        for (const tu of resp.tool_uses) {
          try {
            const label = await dispatchTool(tu, active?.id ?? null);
            dispatched.push(label);
          } catch (e) {
            dispatched.push(`❌ ${tu.name}: ${(e as Error).message}`);
          }
        }
      }

      const html = txt
        ? htmlEscape(txt).replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br/>')
        : '<em>(no prose reply)</em>';

      const dispatchedBlock = dispatched.length
        ? `<div style="margin-top:8px;padding:6px 9px;border-left:2px solid #F09708;background:rgba(240,151,8,.06);border-radius:0 4px 4px 0;font:500 11px/1.5 'Pretendard',sans-serif;color:#E2E8F0">` +
          dispatched.map((d) => `▸ ${htmlEscape(d)}`).join('<br/>') +
          `</div>`
        : '';

      useWorkspace.getState().updateCell(id, {
        answer: { text: [html + dispatchedBlock] },
      });
    } catch (e) {
      const msg = (e as Error).message || 'unknown error';
      useWorkspace.getState().updateCell(id, {
        answer: { text: [
          `<b style="color:#f87171">Claude endpoint error</b><br/>${htmlEscape(msg)}<br/><br/>` +
          `Checklist:<ul>` +
          `<li><code>ANTHROPIC_API_KEY</code> env var set before <code>python3 run.py</code></li>` +
          `<li>Server running on port 8000 (check <code>/health</code>)</li>` +
          `<li>Model <code>claude-haiku-4-5</code> accessible from this key/workspace</li>` +
          `</ul>`,
        ] },
      });
      showToast(`Claude: ${msg}`);
    }
  }

  function htmlEscape(s: string): string {
    return s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c] as string));
  }

  return (
    <div className="llm-dock">
      <div className="llm-dock-inner">
        <div className="llm-ctx">
          <span className="lbl">Context</span>
          {active && <span className={`ds-chip ${active.tag}`}>{active.name}</span>}
          <span style={{ color: '#6B7280', fontSize: 10 }}>{cells.length} cells</span>
        </div>
        <div className="llm-input-wrap">
          <span className="prefix">▸ ASK</span>
          <input
            value={q}
            placeholder='"IEEE 2-col force 그래프 만들어줘" · "Run paired t-test on L vs R force"'
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
          />
          <button className="send" onClick={send}><Send size={14} /></button>
        </div>
      </div>
    </div>
  );
}

async function dispatchTool(tu: ToolUseBlock, activeDsId: string | null): Promise<string> {
  const store = useWorkspace.getState();
  const input = tu.input || {};

  // Every cell-spawning tool needs an active dataset
  const needsDs = ['add_graph_cell', 'add_compute_cell', 'add_stat_cell',
                   'apply_recipe', 'run_all', 'export_bundle'];
  if (needsDs.includes(tu.name) && !activeDsId) {
    throw new Error('no active dataset — upload a CSV first');
  }

  const newId = () => 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);

  switch (tu.name) {
    case 'add_graph_cell': {
      const id = newId();
      store.addCell({
        id, type: 'graph',
        graph: String(input.template || 'force'),
        dsIds: [activeDsId as string],
        preset: input.preset ? String(input.preset) : undefined,
        previewVariant: input.variant ? String(input.variant) as 'col1' | 'col2' | 'onehalf' : undefined,
        strideAvg: !!input.stride_avg,
        title: input.title ? String(input.title) : undefined,
        loading: true,
      });
      store.runPreview(id);
      return `Added graph cell · ${input.template}${input.preset ? ` · ${input.preset}` : ''}`;
    }

    case 'add_compute_cell': {
      const id = newId();
      store.addCell({
        id, type: 'compute',
        metric: String(input.metric || 'per_stride'),
        dsIds: [activeDsId as string],
        loading: true,
      });
      store.runCompute(id);
      return `Added compute cell · ${input.metric}`;
    }

    case 'add_stat_cell': {
      const id = newId();
      store.addCell({
        id, type: 'stat',
        op: String(input.op || 'ttest_paired'),
        inputs: { a: String(input.a_col || ''), b: String(input.b_col || '') },
        dsIds: [activeDsId as string],
        fmt: 'apa',
        loading: true,
      });
      store.runStat(id);
      return `Added stat cell · ${input.op} (${input.a_col}${input.b_col ? ` vs ${input.b_col}` : ''})`;
    }

    case 'apply_recipe': {
      await store.applyRecipes(activeDsId as string);
      return 'Applied canonical recipes';
    }

    case 'set_journal_preset': {
      const p = String(input.preset || 'ieee');
      store.setGlobalPreset(p);
      return `Journal preset → ${p.toUpperCase()}`;
    }

    case 'set_mode': {
      // Mode toggle removed in Phase 2E — publication styling is always on.
      return `(set_mode is a no-op; publication styling is always active)`;
    }

    case 'run_all': {
      await store.runAll();
      return 'Re-ran all bound cells';
    }

    case 'export_bundle': {
      store.showToast('Bundle export: open the Export drawer to download');
      return `(export_bundle called — use the drawer UI to download)`;
    }

    default:
      throw new Error(`unknown tool '${tu.name}'`);
  }
}
