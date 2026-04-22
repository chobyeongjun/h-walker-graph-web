import { Home, BarChart3, Download, Settings } from 'lucide-react';
import { useWorkspace, type DrawerKind } from '../store/workspace';

interface Item {
  icon: React.ReactNode;
  label: string;
  kind?: DrawerKind;
}

const ITEMS: Item[] = [
  { icon: <Home size={18} />, label: 'Workspace' },
  { icon: <BarChart3 size={18} />, label: 'Stats library', kind: 'stats' },
  { icon: <Download size={18} />, label: 'Exports', kind: 'exports' },
  { icon: <Settings size={18} />, label: 'Settings', kind: 'settings' },
];

export default function Sidebar() {
  const drawer = useWorkspace((s) => s.drawer);
  const openDrawer = useWorkspace((s) => s.openDrawer);

  return (
    <aside className="sidebar">
      {ITEMS.map((it, i) => (
        <button
          key={i}
          className={`side-item${it.kind && drawer === it.kind ? ' active' : ''}`}
          onClick={() => it.kind && openDrawer(it.kind)}
        >
          {it.icon}
          <span>{it.label}</span>
        </button>
      ))}
      <div className="side-sep" />
    </aside>
  );
}
