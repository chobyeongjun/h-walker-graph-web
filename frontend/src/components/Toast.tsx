import { useEffect, useState } from 'react';
import { usePage } from '../store/page';

// 2.2 s was too short: on CSV upload a cascade of toasts fired and
// disappeared before the user could read even the first one ("was it
// uploaded?"). 5 s gives the message enough dwell time while still
// auto-clearing, and a click dismisses immediately.
const TOAST_MS = 5000;

export default function Toast() {
  const toast = usePage((s) => s.toast);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!toast) return;
    setVisible(true);
    const id = setTimeout(() => setVisible(false), TOAST_MS);
    return () => clearTimeout(id);
  }, [toast]);

  if (!toast) return null;
  return (
    <div
      className={`toast${visible ? ' on' : ''}`}
      onClick={() => setVisible(false)}
      role="status"
      title="Click to dismiss"
    >
      {toast.msg}
    </div>
  );
}
