import { useState, useEffect, useRef } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { usePage, type Cell } from '../store/page';
import { claudeComplete, type ToolUseBlock } from '../api';
import { GRAPH_TPLS } from '../data/graphTemplates';
import { COMPUTE_METRICS } from '../data/computeMetrics';
import { STAT_OPS } from '../data/statOps';

export default function LlmDock() {
  const [q, setQ] = useState('');
  const datasets = usePage((s) => s.datasets);
  const cells = usePage((s) => s.cells);
  const addCell = usePage((s) => s.addCell);
  const showToast = usePage((s) => s.showToast);
  const logHistory = usePage((s) => s.logHistory);
  const active = datasets.find((d) => d.active);
  const listRef = useRef<HTMLDivElement>(null);

  const llmCells = cells.filter((c) => c.type === 'llm');

  // Auto-scroll the conversation to the latest message.
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [llmCells.length, llmCells[llmCells.length - 1]?.answer?.text.join('').length]);

  async function send() {
    const prompt = q.trim();
    if (!prompt) return;
    setQ('');
    const id = 'c' + Date.now();

    const optimistic: Cell = {
      id, type: 'llm', dsIds: active ? [active.id] : [],
      prompt,
      refs: cells.slice(-2).map((c) => c.id),
      answer: { text: ['<em>Thinking…</em>'] },
    };
    addCell(optimistic);
    logHistory({
      kind: 'chat', actor: 'you',
      label: `Asked: "${prompt.slice(0, 100)}${prompt.length > 100 ? '…' : ''}"`,
      meta: { prompt },
    });

    // Build the prior conversation as message pairs so Claude has multi-
    // turn memory. Each existing llm cell contributes one (user, assistant)
    // pair — answer text has HTML stripped to stay within token budget.
    const priorLlm = cells.filter((c) => c.type === 'llm' && c.prompt);
    const priorTurns = priorLlm.slice(-6).flatMap<{ role: 'user' | 'assistant'; content: string }>((c) => {
      const userTurn = { role: 'user' as const, content: c.prompt || '' };
      const txt = (c.answer?.text || []).join('\n').replace(/<[^>]+>/g, '').trim();
      if (!txt || txt === '(no prose reply)' || txt === '(empty response)') return [userTurn];
      return [userTurn, { role: 'assistant' as const, content: txt }];
    });

    // Phase 2I · include analysis summary of every bound dataset so
    // Claude can reason about anomalies (e.g. "why is the L peak
    // dropping after stride 12?") without a separate lookup round-trip.
    const datasetSummaries = datasets.slice(0, 6).map((d) => {
      const a = d.analysis;
      if (!a || !('mode' in a) || a.mode !== 'hwalker') {
        return { id: d.id, name: d.name, kind: d.kind, group: d.condition };
      }
      return {
        id: d.id,
        name: d.name,
        kind: d.kind,
        group: d.condition,
        n_samples: a.n_samples,
        duration_s: a.duration_s,
        sample_rate: a.sample_rate,
        L: {
          n_strides: a.left.n_strides,
          cadence: a.left.cadence,
          stride_time_mean: a.left.stride_time_mean,
          stride_time_cv: a.left.stride_time_cv,
          force_rmse: a.left.force_tracking.rmse,
        },
        R: {
          n_strides: a.right.n_strides,
          cadence: a.right.cadence,
          stride_time_mean: a.right.stride_time_mean,
          stride_time_cv: a.right.stride_time_cv,
          force_rmse: a.right.force_tracking.rmse,
        },
        symmetry: a.symmetry,
        fatigue: a.fatigue,
      };
    });

    try {
      const resp = await claudeComplete({
        prompt,
        context: {
          cells: cells.map((c) => ({ id: c.id, type: c.type, graph: c.graph, op: c.op, metric: c.metric })),
          active_dataset_id: active?.id ?? null,
          history: priorTurns,
          datasets: datasetSummaries,
        },
      });

      const txt = (resp.reply || '').trim();
      const dispatched: string[] = [];
      if (resp.tool_uses && resp.tool_uses.length) {
        for (const tu of resp.tool_uses) {
          try {
            const label = await dispatchTool(tu, active?.id ?? null);
            dispatched.push(label);
            logHistory({
              kind: 'tool', actor: 'Claude',
              label: `Tool · ${tu.name} → ${label}`,
              meta: { tool: tu.name, input: tu.input },
            });
          } catch (e) {
            const err = (e as Error).message;
            dispatched.push(`❌ ${tu.name}: ${err}`);
            logHistory({
              kind: 'tool', actor: 'Claude',
              label: `Tool · ${tu.name} failed: ${err}`,
            });
          }
        }
      }
      if (txt) {
        logHistory({
          kind: 'chat', actor: 'Claude',
          label: `Replied: "${txt.slice(0, 100)}${txt.length > 100 ? '…' : ''}"`,
          meta: { reply: txt },
        });
      }

      const html = txt
        ? htmlEscape(txt).replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br/>')
        : '<em>(no prose reply)</em>';

      const dispatchedBlock = dispatched.length
        ? `<div style="margin-top:8px;padding:6px 9px;border-left:2px solid #F09708;background:rgba(240,151,8,.06);border-radius:0 4px 4px 0;font:500 11px/1.5 'Pretendard',sans-serif;color:#E2E8F0">` +
          dispatched.map((d) => `▸ ${htmlEscape(d)}`).join('<br/>') +
          `</div>`
        : '';

      usePage.getState().updateCell(id, {
        answer: { text: [html + dispatchedBlock] },
      });
    } catch (e) {
      const msg = (e as Error).message || 'unknown error';
      usePage.getState().updateCell(id, {
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
    <div className="chat">
      <header className="chat-head">
        <Sparkles size={14} style={{ color: '#A78BFA' }} />
        <div className="chat-head-title">Assistant</div>
        <div className="chat-head-meta">Claude Haiku 4.5</div>
      </header>

      <div className="chat-ctx">
        {active ? (
          <>
            <span className="lbl">Context</span>
            <span className={`ds-chip ${active.tag}`}>{active.name}</span>
            <span className="chat-ctx-sub">· {cells.filter((c) => c.type !== 'llm').length} cells</span>
          </>
        ) : (
          <span className="chat-ctx-sub">No active dataset · upload a CSV first</span>
        )}
      </div>

      <div className="chat-list" ref={listRef}>
        {llmCells.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-title">What can I help with?</div>
            <div className="chat-empty-hint">
              <p>Try asking:</p>
              <ul>
                <li>"IEEE 2-col force 그래프 만들어줘"</li>
                <li>"Run paired t-test on L_ActForce_N vs R_ActForce_N"</li>
                <li>"Apply the default analysis"</li>
                <li>"Switch to Nature preset"</li>
              </ul>
            </div>
          </div>
        ) : (
          llmCells.map((c) => (
            <div key={c.id} className="chat-msg">
              <div className="chat-user">
                <span className="chat-role">You</span>
                <div className="chat-bubble you">{c.prompt || ''}</div>
              </div>
              <div className="chat-assistant">
                <span className="chat-role">Claude</span>
                <div
                  className="chat-bubble claude"
                  dangerouslySetInnerHTML={{
                    __html: (c.answer?.text || []).join('<br/><br/>'),
                  }}
                />
              </div>
            </div>
          ))
        )}
      </div>

      <div className="chat-input-wrap">
        <input
          className="chat-input"
          value={q}
          placeholder="말로 그래프 만들거나 통계 돌리기 — Enter to send"
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
        />
        <button className="chat-send" onClick={send} disabled={!q.trim()}>
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}

async function dispatchTool(tu: ToolUseBlock, activeDsId: string | null): Promise<string> {
  const store = usePage.getState();
  const input = tu.input || {};

  const needsDs = ['add_graph_cell', 'add_compute_cell', 'add_stat_cell',
                   'apply_recipe', 'run_all', 'export_bundle'];
  if (needsDs.includes(tu.name) && !activeDsId) {
    throw new Error('no active dataset — upload a CSV first');
  }

  const newId = () => 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);

  switch (tu.name) {
    case 'add_graph_cell': {
      // Validate template before mounting the cell — otherwise an
      // unknown id (e.g. LLM hallucinates "heatmap") leaves a forever-
      // loading shell on the canvas. Reject upfront with a clear message.
      const tpl = String(input.template || 'force');
      if (!(tpl in GRAPH_TPLS)) {
        const close = Object.keys(GRAPH_TPLS).slice(0, 6).join(', ');
        throw new Error(
          `unknown graph template '${tpl}'. Try: ${close}…`
        );
      }
      const id = newId();
      store.addCell({
        id, type: 'graph',
        graph: tpl,
        dsIds: [activeDsId as string],
        preset: input.preset ? String(input.preset) : undefined,
        previewVariant: input.variant ? String(input.variant) as 'col1' | 'col2' | 'onehalf' : undefined,
        strideAvg: !!input.stride_avg,
        title: input.title ? String(input.title) : undefined,
        loading: true,
      });
      store.runPreview(id);
      return `Added graph cell · ${tpl}${input.preset ? ` · ${input.preset}` : ''}`;
    }

    case 'add_compute_cell': {
      const metric = String(input.metric || 'per_stride');
      if (!(metric in COMPUTE_METRICS)) {
        const close = Object.keys(COMPUTE_METRICS).slice(0, 6).join(', ');
        throw new Error(
          `unknown compute metric '${metric}'. Try: ${close}…`
        );
      }
      const id = newId();
      store.addCell({
        id, type: 'compute',
        metric,
        dsIds: [activeDsId as string],
        loading: true,
      });
      store.runCompute(id);
      return `Added compute cell · ${metric}`;
    }

    case 'add_stat_cell': {
      const op = String(input.op || 'ttest_paired');
      if (!(op in STAT_OPS)) {
        const close = Object.keys(STAT_OPS).join(', ');
        throw new Error(`unknown stat op '${op}'. Available: ${close}`);
      }
      const id = newId();
      store.addCell({
        id, type: 'stat',
        op,
        inputs: { a: String(input.a_col || ''), b: String(input.b_col || '') },
        dsIds: [activeDsId as string],
        fmt: 'apa',
        loading: true,
      });
      store.runStat(id);
      return `Added stat cell · ${op} (${input.a_col}${input.b_col ? ` vs ${input.b_col}` : ''})`;
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

    case 'run_paper': {
      // Click the RUN PAPER button programmatically by dispatching a
      // click on its DOM node — the button already handles state
      // + toasts + download.
      const btn = document.querySelector<HTMLButtonElement>(
        'button[title^="Export a ZIP"]'
      );
      if (btn) { btn.click(); return 'Paper bundle exporting…'; }
      store.showToast('RUN PAPER button not found');
      return 'RUN PAPER button not found';
    }

    default:
      throw new Error(`unknown tool '${tu.name}'`);
  }
}
