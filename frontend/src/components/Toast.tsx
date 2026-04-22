import { useEffect, useState } from 'react';
import { usePage } from '../store/page';

export default function Toast() {
  const toast = usePage((s) => s.toast);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!toast) return;
    setVisible(true);
    const id = setTimeout(() => setVisible(false), 2200);
    return () => clearTimeout(id);
  }, [toast]);

  if (!toast) return null;
  return <div className={`toast${visible ? ' on' : ''}`}>{toast.msg}</div>;
}
