import { useRef, useState } from 'react';
import { useWorkspace } from '../store/workspace';
import { CANONICAL_RECIPES } from '../data/canonicalRecipes';
import { uploadDataset } from '../api';

export default function DatasetPanel() {
  const datasets = useWorkspace((s) => s.datasets);
  const setActive = useWorkspace((s) => s.setActiveDataset);
  const openMapper = useWorkspace((s) => s.openMapper);
  const applyRecipes = useWorkspace((s) => s.applyRecipes);
  const toggleRecipe = useWorkspace((s) => s.toggleRecipe);
  const addDataset = useWorkspace((s) => s.addDataset);
  const showToast = useWorkspace((s) => s.showToast);
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const active = datasets.find((d) => d.active) || datasets[0];
  const recipes = active ? CANONICAL_RECIPES[active.kind] || CANONICAL_RECIPES.force : [];

  async function handleFiles(files: FileList | null) {
    if (!files || !files.length) return;
    for (const f of Array.from(files)) {
      if (!f.name.toLowerCase().endsWith('.csv')) continue;
      try {
        const ds = await uploadDataset(f);
        addDataset(ds);
        openMapper(ds.id);
        showToast(`Uploaded ${f.name}`);
      } catch (e) {
        showToast(`Upload failed: ${(e as Error).message}`);
      }
    }
  }

  return (
    <div className="ds-panel">
      <div className="ds-head">
        <span className="ey">DATA SOURCES</span>
        <span className="label">Datasets</span>
        <div className="rest">
          <button className="ds-btn plain" onClick={() => fileRef.current?.click()}>＋ Add CSV</button>
          {active && (
            <button className="ds-btn" onClick={() => openMapper(active.id)}>Map columns</button>
          )}
        </div>
      </div>

      <div className="ds-grid">
        {datasets.map((d) => (
          <div
            key={d.id}
            className={`ds-card${d.active ? ' active' : ''}`}
            onClick={() => setActive(d.id)}
          >
            <div className="ds-row1">
              <span className={`tag ${d.tag}`}>{d.tag}</span>
              <span className="name" title={d.name}>{d.name}</span>
            </div>
            <div className="ds-row2">
              <span><b>{d.rows.toLocaleString()}</b> rows</span>
              <span><b>{d.dur}</b></span>
              <span><b>{d.hz}</b></span>
            </div>
            <div className="ds-cols">
              {d.cols.slice(0, 5).map((c, i) => (
                <span key={i} className={`ds-col${c.mapped && c.mapped !== '—' ? ' mapped' : ''}`}>
                  {c.name}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div
        className={`ds-upload${dragOver ? ' drag' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
      >
        <div className="ds-drop" onClick={() => fileRef.current?.click()}>
          <b>Drop CSV</b>&nbsp;files here, or click to browse
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          multiple
          hidden
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
        />
      </div>

      {recipes.length > 0 && (
        <div className="recipes" style={{ margin: '0 12px 12px' }}>
          <div className="recipes-head">
            <h4>Canonical recipes · {active?.kind}</h4>
            <span className="sub">auto-generated cells based on the dataset type</span>
            {active && (
              <button className="apply" onClick={() => applyRecipes(active.id)}>Apply</button>
            )}
          </div>
          <div className="recipes-grid">
            {recipes.map((r) => {
              const checked = active?.recipeState[r.id] ?? r.default;
              return (
                <label key={r.id} className={`recipe-row${r.default ? ' defaulted' : ''}`}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => active && toggleRecipe(active.id, r.id)}
                  />
                  <span>{r.label}</span>
                  <span className="rtype">{r.type}</span>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
