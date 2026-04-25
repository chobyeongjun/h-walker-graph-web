import { useMemo, useState } from 'react';
import { usePage } from '../store/page';
import { GRAPH_TPLS } from '../data/graphTemplates';
import { COMPUTE_METRICS } from '../data/computeMetrics';
import { STAT_OPS } from '../data/statOps';
import { BookOpen, Search } from 'lucide-react';

/**
 * Click-driven cell catalog — the "bookshelf".
 *
 * Replaces the Haiku/LLM dock per user directive:
 *   "haiku 없애고 모두 다 자동으로 만들어질 수 있도록 클릭으로 바꿔버리자"
 *   "정말 필요한 그림들만 그리고, 그 다음은 미리 만들어놓은 책장에서
 *    책을 꺼내쓰듯이 그래프 그리는 방식들을 모두 다 PreDefine"
 *
 * Every cell type the app knows how to render gets a card here. Click
 * the card → a cell appears on the canvas, bound to the active dataset
 * (or the first dataset if no active one). Nothing else.
 */

interface LibraryItem {
  category: 'Inspect' | 'Force' | 'Kinematics' | 'Temporal' | 'Symmetry' | 'Compute' | 'Stats';
  key: string;
  label: string;
  hint: string;
  add: (dsId: string | null) => void;
}

function newCellId(): string {
  return 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
}

function buildCatalog(
  addCell: ReturnType<typeof usePage.getState>['addCell'],
): LibraryItem[] {
  const items: LibraryItem[] = [];

  // ── Inspector (the MATLAB-style raw signal viewer) ──────────────
  items.push({
    category: 'Inspect',
    key: 'inspector',
    label: 'Raw signal inspector',
    hint: 'Per-sync zoom + pan over any CSV column. Wheel = zoom, drag = pan, ◀▶ = step sync.',
    add: (dsId) => addCell({
      id: newCellId(), type: 'inspector',
      dsIds: dsId ? [dsId] : [],
    }),
  });

  // ── Graphs (one card per template metadata) ─────────────────────
  const graphCategoryOf = (key: string): LibraryItem['category'] => {
    if (key.startsWith('force') || key === 'asymmetry' || key === 'cop' || key === 'trials' || key === 'cv_bar') {
      return 'Force';
    }
    if (key === 'imu_avg' || key === 'cyclogram' || key === 'rom_bar') return 'Kinematics';
    if (key === 'stride_time_trend' || key === 'stance_swing_bar') return 'Temporal';
    if (key === 'symmetry_radar') return 'Symmetry';
    return 'Force';
  };
  for (const [key, tpl] of Object.entries(GRAPH_TPLS)) {
    items.push({
      category: graphCategoryOf(key),
      key: `graph:${key}`,
      label: tpl.title,
      hint: tpl.ey,
      add: (dsId) => addCell({
        id: newCellId(), type: 'graph',
        graph: key,
        dsIds: dsId ? [dsId] : [],
        loading: !!dsId,
      }),
    });
  }

  // ── Compute metrics ─────────────────────────────────────────────
  for (const [key, m] of Object.entries(COMPUTE_METRICS)) {
    items.push({
      category: 'Compute',
      key: `compute:${key}`,
      label: m.label,
      hint: m.cols.join(' · '),
      add: (dsId) => addCell({
        id: newCellId(), type: 'compute',
        metric: key,
        dsIds: dsId ? [dsId] : [],
        loading: !!dsId,
      }),
    });
  }

  // ── Stats ops ───────────────────────────────────────────────────
  for (const [key, op] of Object.entries(STAT_OPS)) {
    items.push({
      category: 'Stats',
      key: `stat:${key}`,
      label: op.label,
      hint: `Needs ${op.needs} input${op.needs === 1 ? '' : 's'}. Configure columns inside the cell.`,
      add: (dsId) => addCell({
        id: newCellId(), type: 'stat',
        op: key,
        inputs: { a: '', b: '' },
        dsIds: dsId ? [dsId] : [],
        fmt: 'apa',
      }),
    });
  }

  return items;
}

const CATEGORIES: LibraryItem['category'][] = [
  'Inspect', 'Force', 'Kinematics', 'Temporal', 'Symmetry', 'Compute', 'Stats',
];

export default function Library() {
  const datasets = usePage((s) => s.datasets);
  const addCell = usePage((s) => s.addCell);
  const showToast = usePage((s) => s.showToast);
  const [query, setQuery] = useState('');
  const [activeCat, setActiveCat] = useState<LibraryItem['category'] | 'All'>('All');

  const active = datasets.find((d) => d.active) || datasets[0];
  const dsId = active?.id ?? null;

  const items = useMemo(() => buildCatalog(addCell), [addCell]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((it) => {
      if (activeCat !== 'All' && it.category !== activeCat) return false;
      if (!q) return true;
      return it.label.toLowerCase().includes(q) || it.hint.toLowerCase().includes(q) || it.key.toLowerCase().includes(q);
    });
  }, [items, query, activeCat]);

  function handleAdd(it: LibraryItem) {
    if (!dsId) {
      showToast('Drop a CSV first — bookshelf items need a dataset.');
      return;
    }
    it.add(dsId);
    showToast(`Added · ${it.label}`);
  }

  return (
    <div className="library" style={{
      display: 'flex', flexDirection: 'column', height: '100%', gap: 8, padding: 10,
    }}>
      <header style={{
        display: 'flex', alignItems: 'center', gap: 6,
        fontFamily: "'Pretendard', sans-serif", fontWeight: 600, fontSize: 12,
        color: '#F09708', letterSpacing: '.18em', textTransform: 'uppercase',
      }}>
        <BookOpen size={14} />
        <span>Library</span>
      </header>

      <div style={{
        position: 'relative', display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <Search size={12} style={{ position: 'absolute', left: 8, color: '#6B7280' }} />
        <input
          type="text" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search figures, metrics, tests…"
          style={{
            flex: 1, paddingLeft: 26, paddingRight: 8, height: 28,
            background: 'rgba(15,23,42,.5)', color: '#E2E8F0',
            border: '1px solid #2D3748', borderRadius: 4,
            fontFamily: "'Pretendard', sans-serif", fontSize: 11,
          }}
        />
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        {(['All', ...CATEGORIES] as const).map((c) => (
          <button
            key={c}
            onClick={() => setActiveCat(c)}
            style={{
              padding: '3px 8px', fontSize: 10, borderRadius: 3,
              border: activeCat === c ? '1px solid #F09708' : '1px solid #2D3748',
              background: activeCat === c ? 'rgba(240,151,8,.15)' : 'transparent',
              color: activeCat === c ? '#F09708' : '#9CA3AF',
              cursor: 'pointer', fontFamily: 'JetBrains Mono, monospace',
            }}
          >
            {c}
          </button>
        ))}
      </div>

      {!dsId && (
        <div style={{
          padding: 10, fontSize: 11, color: '#A78BFA',
          background: 'rgba(167,139,250,.08)', borderRadius: 4,
        }}>
          Drop a CSV anywhere on the page to enable the bookshelf.
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {filtered.map((it) => (
          <button
            key={it.key}
            onClick={() => handleAdd(it)}
            disabled={!dsId}
            style={{
              textAlign: 'left', padding: '7px 9px',
              background: 'rgba(15,23,42,.45)',
              border: '1px solid #1E293B',
              borderLeft: '2px solid #F09708',
              borderRadius: 3,
              cursor: dsId ? 'pointer' : 'not-allowed',
              opacity: dsId ? 1 : 0.5,
              transition: 'all .15s cubic-bezier(.22,1,.36,1)',
            }}
            onMouseEnter={(e) => {
              if (!dsId) return;
              e.currentTarget.style.borderLeftWidth = '4px';
              e.currentTarget.style.background = 'rgba(240,151,8,.06)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderLeftWidth = '2px';
              e.currentTarget.style.background = 'rgba(15,23,42,.45)';
            }}
          >
            <div style={{ fontSize: 11, fontWeight: 600, color: '#E2E8F0' }}>
              {it.label}
            </div>
            <div style={{
              fontSize: 9, color: '#6B7280', marginTop: 2,
              fontFamily: 'JetBrains Mono, monospace',
            }}>
              {it.category} · {it.hint}
            </div>
          </button>
        ))}
        {filtered.length === 0 && (
          <div style={{ padding: 18, color: '#6B7280', fontSize: 11, textAlign: 'center' }}>
            No matches.
          </div>
        )}
      </div>

      <footer style={{ color: '#6B7280', fontSize: 9, fontFamily: 'JetBrains Mono, monospace' }}>
        {items.length} items · click to add to canvas
      </footer>
    </div>
  );
}
