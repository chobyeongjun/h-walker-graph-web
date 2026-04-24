import { useState, useEffect, useRef } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { usePage, type Cell } from '../store/page';
import { claudeComplete, type ToolUseBlock } from '../api';

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
      // Always include column names so Claude can reference them precisely
      // (e.g. 'Analog A7', 'L_GCP') when calling detect_events / column_stats.
      const columns = (d.cols || []).map((c) => c.name);
      const a = d.analysis;
      if (!a || !('mode' in a) || a.mode !== 'hwalker') {
        return { id: d.id, name: d.name, kind: d.kind, group: d.condition, columns };
      }
      return {
        id: d.id,
        name: d.name,
        kind: d.kind,
        group: d.condition,
        columns,
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

    case 'analyze_study': {
      const dir = String(input.directory || '');
      const name = String(input.name || 'Auto Study');
      store.discoverAndRunStudy(dir, name);
      return `Study processing started: ${name} (${dir})`;
    }

    case 'detect_events': {
      if (!activeDsId) throw new Error('no active dataset — upload a CSV first');
      const sigCol = String(input.signal_col || '');
      if (!sigCol) throw new Error('detect_events requires signal_col');
      const id = newId();
      store.addCell({
        id, type: 'compute',
        metric: `events:${sigCol}`,
        dsIds: [activeDsId],
        loading: true,
      });
      const resp = await fetch('/api/compute/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_id: activeDsId,
          signal_col: sigCol,
          threshold: input.threshold ?? null,
          min_duration_s: input.min_duration_s ?? 0.1,
        }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        store.updateCell(id, { loading: false, error: err.detail || 'detect_events failed' });
        throw new Error(err.detail || 'detect_events failed');
      }
      const data = await resp.json();
      store.updateCell(id, { loading: false, computeData: data });
      return `Event detection: ${data.meta?.n_events ?? '?'} events in "${sigCol}" (threshold ${data.meta?.threshold ?? '?'})`;
    }

    case 'column_stats': {
      if (!activeDsId) throw new Error('no active dataset — upload a CSV first');
      const cols: string[] = Array.isArray(input.columns)
        ? input.columns.map(String)
        : [String(input.columns || '')];
      if (!cols.length || !cols[0]) throw new Error('column_stats requires columns list');
      const id = newId();
      store.addCell({
        id, type: 'compute',
        metric: `colstats:${cols.slice(0, 2).join(',')}`,
        dsIds: [activeDsId],
        loading: true,
      });
      const resp = await fetch('/api/compute/column_stats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_id: activeDsId, columns: cols }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        store.updateCell(id, { loading: false, error: err.detail || 'column_stats failed' });
        throw new Error(err.detail || 'column_stats failed');
      }
      const data = await resp.json();
      store.updateCell(id, { loading: false, computeData: data });
      return `Column stats: ${cols.join(', ')}`;
    }

    case 'detect_mocap_windows': {
      if (!activeDsId) throw new Error('no active dataset — upload a CSV first');
      const id = newId();
      store.addCell({
        id, type: 'compute',
        metric: `mocap:windows`,
        dsIds: [activeDsId],
        loading: true,
      });
      const mBody: Record<string, unknown> = { dataset_id: activeDsId };
      if (input.sync_col) mBody.sync_col = String(input.sync_col);
      if (input.min_duration_s != null) mBody.min_duration_s = Number(input.min_duration_s);
      const mResp = await fetch('/api/compute/mocap_windows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mBody),
      });
      if (!mResp.ok) {
        const err = await mResp.json().catch(() => ({ detail: mResp.statusText }));
        store.updateCell(id, { loading: false, error: err.detail || 'mocap_windows failed' });
        throw new Error(err.detail || 'mocap_windows failed');
      }
      const mData = await mResp.json();
      store.updateCell(id, { loading: false, computeData: mData });
      const n = mData.meta?.n_windows ?? '?';
      const sc = mData.meta?.sync_col ?? '';
      return `MoCap 구간 감지: ${n}개 구간 (${sc}) — 구간별 그래프는 "1번 구간 보여줘"로 요청하세요.`;
    }

    case 'view_time_window': {
      if (!activeDsId) throw new Error('no active dataset — upload a CSV first');
      const tStart = Number(input.time_start);
      const tEnd = Number(input.time_end);
      const dur = (tEnd - tStart).toFixed(1);
      const wTitle = input.title
        ? String(input.title)
        : `MoCap 구간 · ${tStart.toFixed(1)}s – ${tEnd.toFixed(1)}s (${dur}s)`;
      const id = newId();
      store.addCell({
        id, type: 'graph',
        graph: 'debug_ts',
        dsIds: [activeDsId],
        title: wTitle,
        timeStart: tStart,
        timeEnd: tEnd,
        loading: true,
      });
      store.runPreview(id);
      return `시간 창 그래프 추가: ${wTitle}`;
    }

    default:
      throw new Error(`unknown tool '${tu.name}'`);
  }
}
