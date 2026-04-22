import { useEffect, useRef, useState } from 'react';
import { Upload } from 'lucide-react';
import { useWorkspace } from '../store/workspace';
import { uploadDataset } from '../api';

/**
 * Window-level CSV drop overlay.
 *
 * Listens for `dragenter` on the entire window and shows a full-screen
 * dropzone so the user can release the file anywhere. Without this,
 * dropping slightly outside the narrow DatasetPanel strip triggers the
 * browser's default action (downloading/opening the CSV), and it looks
 * like drag-and-drop doesn't work.
 *
 * Also prevents the browser default on window `dragover`, which is the
 * second half of the fix — browsers refuse `drop` events unless the
 * parent element preventDefault's on `dragover` first.
 */
export default function GlobalDropZone() {
  const addDataset = useWorkspace((s) => s.addDataset);
  const setActive = useWorkspace((s) => s.setActiveDataset);
  const applyRecipes = useWorkspace((s) => s.applyRecipes);
  const showToast = useWorkspace((s) => s.showToast);
  const [active, setActiveDrop] = useState(false);
  const counter = useRef(0);

  useEffect(() => {
    function hasFiles(e: DragEvent): boolean {
      return !!e.dataTransfer && Array.from(e.dataTransfer.types).includes('Files');
    }

    function onEnter(e: DragEvent) {
      if (!hasFiles(e)) return;
      e.preventDefault();
      counter.current += 1;
      setActiveDrop(true);
    }
    function onOver(e: DragEvent) {
      if (!hasFiles(e)) return;
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    }
    function onLeave(e: DragEvent) {
      if (!hasFiles(e)) return;
      counter.current -= 1;
      if (counter.current <= 0) {
        counter.current = 0;
        setActiveDrop(false);
      }
    }
    async function onDrop(e: DragEvent) {
      if (!hasFiles(e)) return;
      e.preventDefault();
      counter.current = 0;
      setActiveDrop(false);
      const files = e.dataTransfer?.files;
      if (!files || !files.length) return;

      let accepted = 0;
      const skipped: string[] = [];
      for (const f of Array.from(files)) {
        const n = f.name.toLowerCase();
        const looksCsv = /\.csv(\b|$|\s|\.)/.test(n) || !/\.\w+$/.test(n);
        if (!looksCsv) {
          skipped.push(f.name);
          continue;
        }
        try {
          const ds = await uploadDataset(f);
          addDataset(ds);
          setActive(ds.id);
          showToast(`Uploaded ${f.name} · running default recipes…`);
          applyRecipes(ds.id).catch((err) =>
            showToast(`Auto-run failed: ${(err as Error).message}`),
          );
          accepted += 1;
        } catch (err) {
          showToast(`Upload failed (${f.name}): ${(err as Error).message}`);
        }
      }
      if (accepted === 0 && skipped.length) {
        showToast(
          `Not CSV files: ${skipped.slice(0, 3).join(', ')}${skipped.length > 3 ? '…' : ''}`,
        );
      }
    }

    window.addEventListener('dragenter', onEnter);
    window.addEventListener('dragover', onOver);
    window.addEventListener('dragleave', onLeave);
    window.addEventListener('drop', onDrop);
    return () => {
      window.removeEventListener('dragenter', onEnter);
      window.removeEventListener('dragover', onOver);
      window.removeEventListener('dragleave', onLeave);
      window.removeEventListener('drop', onDrop);
    };
  }, [addDataset, setActive, applyRecipes, showToast]);

  if (!active) return null;

  return (
    <div className="global-drop">
      <div className="global-drop-inner">
        <Upload size={56} />
        <div className="global-drop-title">Drop CSV to upload</div>
        <div className="global-drop-sub">
          Releases the file anywhere — default recipes auto-run on arrival.
        </div>
      </div>
    </div>
  );
}
