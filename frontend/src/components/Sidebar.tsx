import { Home, History, BarChart3, Download, Settings } from 'lucide-react';
import { usePage, type DrawerKind } from '../store/page';

interface Item {
  icon: React.ReactNode;
  label: string;
  kind?: DrawerKind;
}

const ITEMS: Item[] = [
  { icon: <Home size={18} />, label: 'Page' },
  { icon: <History size={18} />, label: 'History', kind: 'history' },
  { icon: <BarChart3 size={18} />, label: 'Stats library', kind: 'stats' },
  { icon: <Download size={18} />, label: 'Exports', kind: 'exports' },
  { icon: <Settings size={18} />, label: 'Settings', kind: 'settings' },
];

export default function Sidebar() {
  const drawer = usePage((s) => s.drawer);
  const openDrawer = usePage((s) => s.openDrawer);

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
