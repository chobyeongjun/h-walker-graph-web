import { useState } from 'react';
import { Send } from 'lucide-react';
import { useWorkspace, type Cell } from '../store/workspace';
import { claudeComplete } from '../api';

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
      useWorkspace.getState().updateCell(id, {
        answer: { text: txt ? [htmlEscape(txt).replace(/\n\n+/g, '</p><p>').replace(/\n/g, '<br/>')] : ['<em>(empty response)</em>'] },
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
            placeholder='"Compare L/R peak force" · "Run paired t-test on c2"'
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
          />
          <button className="send" onClick={send}><Send size={14} /></button>
        </div>
      </div>
    </div>
  );
}
