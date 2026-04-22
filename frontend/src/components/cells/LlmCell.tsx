import type { Cell } from '../../store/workspace';
import { useWorkspace } from '../../store/workspace';

interface Props { cell: Cell; }

export default function LlmCell({ cell }: Props) {
  const showToast = useWorkspace((s) => s.showToast);
  return (
    <>
      {cell.prompt && (
        <div className="llm-prompt">
          <span className="quoteb">Q</span>
          <div>
            <div>{cell.prompt}</div>
            {cell.refs && cell.refs.length > 0 && (
              <div className="refs">
                {cell.refs.map((r) => (
                  <span key={r} className="ref-chip" onClick={() => {
                    const el = document.getElementById(`cell-${r}`);
                    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  }}>{r}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      {cell.answer && (
        <div className="llm-response">
          {cell.answer.text.map((p, i) => (
            <p key={i} dangerouslySetInnerHTML={{ __html: p }} />
          ))}
          {cell.answer.spawns && cell.answer.spawns.length > 0 && (
            <div className="llm-spawns">
              {cell.answer.spawns.map((s, i) => (
                <button key={i} className="llm-spawn" onClick={() => showToast(`Spawn: ${s.action}`)}>
                  {s.label}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
