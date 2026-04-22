/* ============================================================
   H-Walker CORE · Phase 2 — Analysis Workspace
   ============================================================ */

const COLORS = {
  lActual:'#3B82C4', lDesired:'#7FB5E4',
  rActual:'#D35454', rDesired:'#E89B9B',
  accent:'#F09708', mint:'#00FFB2', violet:'#A78BFA',
};

/* ============================================================
   Datasets — synthetic but with realistic columns
   ============================================================ */
const DATASETS = [
  {
    id:'ds1', name:'trial_1_force.csv', tag:'force', kind:'force',
    rows:2400, dur:'24.0s', hz:'100Hz',
    cols:[
      {name:'time_s',  mapped:'time',     unit:'s'},
      {name:'L_force', mapped:'L force',  unit:'N'},
      {name:'R_force', mapped:'R force',  unit:'N'},
      {name:'L_cop',   mapped:'—',        unit:'mm'},
      {name:'R_cop',   mapped:'—',        unit:'mm'},
    ],
    active:true,
  },
  {
    id:'ds2', name:'trial_2_imu.csv', tag:'imu', kind:'imu',
    rows:800, dur:'8.0s', hz:'100Hz',
    cols:[
      {name:'t',        mapped:'time',   unit:'s'},
      {name:'shank_pitch', mapped:'shank', unit:'°'},
      {name:'thigh_pitch', mapped:'thigh', unit:'°'},
      {name:'shank_roll',  mapped:'—',    unit:'°'},
    ],
    active:false,
  },
  {
    id:'ds3', name:'pilot_run.csv', tag:'mix', kind:'trials',
    rows:5000, dur:'50.0s · 5 trials', hz:'100Hz',
    cols:[
      {name:'time',    mapped:'time',    unit:'s'},
      {name:'trial_id',mapped:'group',   unit:'—'},
      {name:'force',   mapped:'force',   unit:'N·n'},
    ],
    active:false,
  },
];

/* ============================================================
   Graph templates — path data + tick labels + summary stats
   ============================================================ */
const GRAPH_TPLS = {
  force:{
    ey:'Force · L vs R', title:'Ground reaction force', ds:'ds1',
    yUnit:'Force (N)', xUnit:'Gait cycle (%)',
    paths:[
      {c:COLORS.lActual, w:2,   label:'L Actual',  d:'M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138'},
      {c:COLORS.lDesired,w:1.3, label:'L Desired', dash:'4 3', d:'M48,164 C70,160 92,126 114,78 C138,42 158,34 180,48 C204,62 224,82 246,112 C270,140 292,154 312,152 C332,148 354,134 376,124 C394,116 402,124 408,140'},
      {c:COLORS.rActual, w:2,   label:'R Actual',  d:'M48,165 C70,160 92,150 114,108 C138,62 160,48 180,64 C202,82 224,100 246,130 C270,150 292,156 312,152 C332,150 354,138 376,124 C394,114 402,122 408,136'},
      {c:COLORS.rDesired,w:1.3, label:'R Desired', dash:'4 3', d:'M48,167 C70,162 92,154 114,114 C138,68 160,54 180,70 C202,88 224,104 246,132 C270,150 292,156 312,154 C332,150 354,138 376,126 C394,114 402,124 408,138'},
    ],
    yTicks:['60','45','30','15','0'], xTicks:['0','25','50','75','100'],
    summary:[['n strides','14'],['peak ΔL','48.2 N'],['peak ΔR','46.7 N'],['asym','3.2%']],
  },
  imu:{
    ey:'IMU · Pitch', title:'Shank vs thigh pitch', ds:'ds2',
    yUnit:'Pitch (°)', xUnit:'Time (s)',
    paths:[
      {c:COLORS.lActual, w:1.8, label:'Shank', d:'M48,100 C70,70 92,40 114,50 C136,60 158,130 180,140 C202,150 224,90 246,60 C268,50 290,110 312,140 C332,150 354,100 376,70 C394,55 402,80 408,100'},
      {c:COLORS.rActual, w:1.8, label:'Thigh', d:'M48,110 C70,90 92,70 114,78 C138,88 158,120 180,126 C204,132 224,100 246,82 C268,75 290,108 312,128 C332,136 354,108 376,88 C394,78 402,90 408,102'},
    ],
    yTicks:['+20','+10','0','−10','−20'], xTicks:['0','2','4','6','8'],
    summary:[['strides','3'],['cadence','112 spm'],['stride T','1.08 s']],
  },
  force_avg:{
    ey:'Force · mean ± SD', title:'GRF stride-averaged (n=14)', ds:'ds1',
    yUnit:'Vertical GRF (N)', xUnit:'Gait cycle (%)',
    bands:[
      {c:'#3B82C4',opacity:.18,
        upper:'M48,148 C70,144 92,108 114,58 C138,24 158,14 180,28 C202,44 224,66 246,96 C270,126 290,138 312,136 C332,134 354,120 376,108 C394,100 402,108 408,124',
        lower:'M48,172 C70,167 92,132 114,86 C138,52 158,42 180,56 C202,72 224,94 246,124 C270,154 290,166 312,164 C332,162 354,148 376,136 C394,128 402,136 408,152'},
      {c:'#D35454',opacity:.18,
        upper:'M48,153 C70,148 92,138 114,94 C138,48 160,34 180,50 C202,68 224,86 246,116 C270,136 292,142 312,138 C332,136 354,124 376,110 C394,100 402,108 408,122',
        lower:'M48,177 C70,172 92,162 114,122 C138,76 160,62 180,78 C202,96 224,114 246,144 C270,164 292,170 312,166 C332,164 354,152 376,138 C394,128 402,136 408,150'},
    ],
    paths:[
      {c:'#1E5F9E',w:2,label:'L mean',d:'M48,160 C70,155 92,120 114,72 C138,38 158,28 180,42 C202,58 224,80 246,110 C270,140 290,152 312,150 C332,148 354,134 376,122 C394,114 402,122 408,138'},
      {c:'#9E3838',w:2,label:'R mean',d:'M48,165 C70,160 92,150 114,108 C138,62 160,48 180,64 C202,82 224,100 246,130 C270,150 292,156 312,152 C332,150 354,138 376,124 C394,114 402,122 408,136'},
    ],
    yTicks:['60','45','30','15','0'], xTicks:['0','25','50','75','100'],
    summary:[['n strides','14'],['mean peak L','48.2 ± 0.6 N'],['mean peak R','46.7 ± 0.7 N'],['CV','1.3%']],
  },
  asymmetry:{
    ey:'Asymmetry · per stride', title:'Asymmetry index across strides', ds:'ds1',
    yUnit:'Asymmetry (%)', xUnit:'Stride #',
    paths:[
      {c:'#F09708',w:1.8,label:'asym_idx',d:'M48,120 L76,98 L102,115 L128,105 L156,90 L184,110 L210,95 L238,118 L264,100 L292,85 L318,112 L348,102 L376,92 L408,106'},
    ],
    hlines:[{y:140,c:'#6B7280',dash:'3 3',label:'5% threshold'}],
    yTicks:['10','7.5','5','2.5','0'], xTicks:['1','4','7','10','14'],
    summary:[['mean','2.1 ± 0.8%'],['max','3.6%'],['≥5%','0 strides']],
  },
  peak_box:{
    ey:'Peak force · L vs R', title:'Peak vertical GRF — boxplot', ds:'ds1',
    yUnit:'Peak GRF (N)', xUnit:'',
    boxes:[
      {x:140,label:'L',c:'#3B82C4',min:170,q1:162,med:158,q3:155,max:148},
      {x:280,label:'R',c:'#D35454',min:175,q1:167,med:163,q3:160,max:152},
    ],
    yTicks:['50','48','46','44','42'], xTicks:[],
    summary:[['n=14','paired'],['Δ mean','+1.5 N'],['p','.006']],
  },
  cop:{
    ey:'CoP · trajectory', title:'Center of pressure path', ds:'ds1',
    yUnit:'AP (mm)', xUnit:'ML (mm)',
    paths:[
      {c:'#3B82C4',w:1.6,label:'L CoP',d:'M100,160 C110,140 115,120 120,100 C125,80 130,60 140,40 C145,35 150,35 155,40'},
      {c:'#D35454',w:1.6,label:'R CoP',d:'M300,160 C295,140 290,120 285,100 C280,80 275,60 268,40 C263,35 258,35 255,40'},
    ],
    yTicks:['+50','+25','0','−25','−50'], xTicks:['−40','−20','0','+20','+40'],
    summary:[['L path','142 mm'],['R path','138 mm'],['Δ','+2.9%']],
  },
  cv_bar:{
    ey:'Variability · CV', title:'Coefficient of variation per trial', ds:'ds3',
    yUnit:'CV (%)', xUnit:'Trial',
    bars:[
      {x:80, w:40, h:60, c:'#7FB5E4', label:'T1'},
      {x:150,w:40, h:48, c:'#3B82C4', label:'T2'},
      {x:220,w:40, h:36, c:'#E89B9B', label:'T3'},
      {x:290,w:40, h:22, c:'#D35454', label:'T4'},
      {x:360,w:40, h:14, c:'#F09708', label:'T5'},
    ],
    yTicks:['8','6','4','2','0'], xTicks:['T1','T2','T3','T4','T5'],
    summary:[['trials','5'],['improving','T1→T5'],['final CV','0.7%']],
  },
  trials:{
    ey:'Trials · N=5', title:'Trial overlay', ds:'ds3',
    yUnit:'Normalized force', xUnit:'Gait cycle (%)',
    paths:[
      {c:'#7FB5E4',w:1.4,label:'Trial 1',d:'M48,170 C82,150 112,100 150,60 C188,40 222,32 258,52 C292,78 326,130 360,160 C384,172 398,168 408,164'},
      {c:'#3B82C4',w:1.4,label:'Trial 2',d:'M48,172 C82,154 112,104 150,66 C188,46 222,38 258,58 C292,82 326,132 360,160 C384,170 398,168 408,166'},
      {c:'#E89B9B',w:1.4,label:'Trial 3',d:'M48,168 C82,148 112,98 150,58 C188,38 222,30 258,50 C292,76 326,128 360,158 C384,170 398,166 408,162'},
      {c:'#D35454',w:1.4,label:'Trial 4',d:'M48,174 C82,156 112,108 150,70 C188,50 222,42 258,60 C292,84 326,134 360,162 C384,172 398,170 408,168'},
      {c:COLORS.accent,w:2.2,label:'Trial 5 · target',d:'M48,166 C82,146 112,94 150,54 C188,34 222,26 258,46 C292,72 326,124 360,154 C384,168 398,164 408,160'},
    ],
    yTicks:['1.0','0.75','0.5','0.25','0'], xTicks:['0','25','50','75','100'],
    summary:[['trials','5'],['CV','4.1%'],['target Δ','+2.3%']],
  },
};

/* ============================================================
   Statistical machinery — deterministic mock results.
     Real impl: Claude Code will back these with SciPy on server.
   ============================================================ */
const STAT_OPS = {
  ttest_paired:{ label:'Paired t-test', needs:2,
    run:({a,b})=>{
      // Deterministic pseudo-result seeded by series labels
      const seed = (a+b).length;
      return {
        test:'Paired t-test (two-tailed)',
        n: 14,
        t: (3.27 + (seed%4)*.08).toFixed(2),
        df: 13,
        p: '0.006',
        psig: true,
        mean_diff: '+4.82 N',
        ci95: '[1.62, 8.02]',
        cohen_d: '0.87',
        effect: 'large',
      };
    }
  },
  ttest_welch:{ label:'Welch t-test', needs:2,
    run:()=>({test:'Welch t-test (two-tailed)',n1:14,n2:14,t:'2.94',df:'25.8',p:'0.007',psig:true,mean_diff:'+4.6 N',ci95:'[1.3, 7.9]',cohen_d:'0.79',effect:'medium-large'})
  },
  anova:{ label:'One-way ANOVA', needs:3,
    run:()=>({test:'One-way ANOVA',k:3,n:42,F:'5.14',df1:2,df2:39,p:'0.011',psig:true,eta2:'0.208',effect:'large',posthoc:'Tukey HSD: T1<T5 (p=.008), T2<T5 (p=.024)'})
  },
  corr:{ label:'Pearson correlation', needs:2,
    run:()=>({test:'Pearson correlation',n:140,r:'0.72',p:'<0.001',psig:true,ci95:'[0.62, 0.80]',effect:'strong positive'})
  },
  cohen:{ label:'Cohen\'s d', needs:2,
    run:()=>({test:'Cohen\'s d (independent)',n1:14,n2:14,cohen_d:'0.87',ci95:'[0.09, 1.64]',effect:'large',mean_diff:'+4.82 N'})
  },
};

/* ============================================================
   Cell model
   ============================================================ */
let cells = [
  { id:'c1', type:'graph', graph:'force' },
  { id:'c2', type:'stat',
    op:'ttest_paired',
    inputs:{ a:'L Actual', b:'R Actual' },
    dsIds:['ds1'], fmt:'apa',
  },
  { id:'c3', type:'graph', graph:'imu' },
  { id:'c4', type:'llm',
    prompt:'Compare L/R peak force asymmetry across c1 and explain the mid-stance deficit.',
    refs:['c1','c2'],
    answer:{
      text:[
        'Across <b>14 strides</b> in <code>trial_1_force.csv</code>, the left limb peaks at <b class="num">48.2 N</b> vs. right at <b class="num">46.7 N</b> — an asymmetry index of <b class="num">3.2%</b>.',
        'The paired-t in c2 confirms the gap is real: <b>t(13) = 3.27, p = .006, d = 0.87</b> (large effect). Most of the Δ sits in <b>mid-stance (30–55% GC)</b> where the R-side loses ≈8N of drive.',
        'Interpretation: <b>late stance-phase propulsion deficit on the right</b>, consistent with a weakened gastrocnemius or delayed heel-off. Recommend overlaying the desired trajectory from the prescription file.',
      ],
      spawns:[
        { label:'+ Graph: isolate 30–55% GC', action:'graph:force:zoom' },
        { label:'+ Stat: ANOVA across 5 trials', action:'stat:anova' },
      ]
    }
  },
];

/* ============================================================
   DOM refs
   ============================================================ */
const cellsEl = document.getElementById('cells');
const mCells = document.getElementById('m-cells');
const mDatasets = document.getElementById('m-datasets');

/* ============================================================
   Render — datasets panel
   ============================================================ */
const dsGrid = document.getElementById('ds-grid');
function renderDatasets(){
  dsGrid.innerHTML = DATASETS.map(d=>{
    const cols = d.cols.map(c=>`<span class="ds-col ${c.mapped!=='—'?'mapped':''}" title="${c.mapped}">${c.name}</span>`).join('');
    return `<div class="ds-card ${d.active?'active':''}" data-id="${d.id}">
      <div class="ds-row1">
        <span class="tag ${d.tag}">${d.tag}</span>
        <span class="name">${d.name}</span>
      </div>
      <div class="ds-row2">
        <span>rows <b>${d.rows.toLocaleString()}</b></span>
        <span>dur <b>${d.dur}</b></span>
        <span>fs <b>${d.hz}</b></span>
      </div>
      <div class="ds-cols">${cols}</div>
    </div>`;
  }).join('');
  dsGrid.querySelectorAll('.ds-card').forEach(c=>{
    c.onclick=()=>{
      DATASETS.forEach(d=>d.active=(d.id===c.dataset.id));
      renderDatasets();
      renderLlmCtx();
      toast('Active dataset: '+DATASETS.find(d=>d.active).name);
    };
  });
  mDatasets.textContent = DATASETS.length;
  renderRecipes();
}

/* Canonical-recipe panel — which derived cells to auto-generate */
function renderRecipes(){
  const host = document.getElementById('ds-recipes');
  if(!host || typeof CANONICAL_RECIPES==='undefined') return;
  const active = DATASETS.find(d=>d.active) || DATASETS[0];
  const kind = active?.kind || 'force';
  const recipes = CANONICAL_RECIPES[kind] || CANONICAL_RECIPES.force || [];
  if(!active.recipeState) active.recipeState = Object.fromEntries(recipes.map(r=>[r.id, r.default]));
  host.innerHTML = `
    <div class="recipes-head">
      <h4>Canonical recipes · ${kind}</h4>
      <span class="sub">${active.name} — auto-generate these cells on apply</span>
      <button class="apply" data-recipe-act="apply">Apply ${recipes.filter(r=>active.recipeState[r.id]).length}</button>
    </div>
    <div class="recipes-grid">
      ${recipes.map(r=>`
        <label class="recipe-row ${r.default?'defaulted':''}">
          <input type="checkbox" data-recipe="${r.id}" ${active.recipeState[r.id]?'checked':''}/>
          <span>${r.label}</span>
          <span class="rtype">${r.type}</span>
        </label>`).join('')}
    </div>`;
  host.querySelectorAll('[data-recipe]').forEach(cb=>{
    cb.addEventListener('change',e=>{
      active.recipeState[cb.dataset.recipe] = cb.checked;
      const n = recipes.filter(r=>active.recipeState[r.id]).length;
      host.querySelector('.apply').textContent = `Apply ${n}`;
    });
  });
  host.querySelector('[data-recipe-act="apply"]').addEventListener('click',()=>{
    const picked = recipes.filter(r=>active.recipeState[r.id]);
    let added = 0;
    picked.forEach(r=>{
      if(r.type==='graph' && GRAPH_TPLS[r.graph]){
        cells.push({id:'c'+Date.now()+'_'+added,type:'graph',graph:r.graph,preset:'ieee'});
        added++;
      } else if(r.type==='compute'){
        // compute → represented as a stat cell with op='ttest' placeholder for now
        cells.push({id:'c'+Date.now()+'_'+added,type:'stat',op:'ttest',
          inputs:{a:'L peak',b:'R peak'},dsIds:[active.id],fmt:'apa'});
        added++;
      }
    });
    renderCells();
    toast(`Added ${added} canonical cells from ${active.name}`);
  });
}

document.getElementById('ds-add').onclick=()=>toast('Drop CSV files into the drop-zone below ↓');
document.getElementById('ds-map').onclick=()=>toast('Claude is auto-mapping columns… 3 inferences.');
const drop = document.getElementById('ds-drop');
drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('drag')});
drop.addEventListener('dragleave',()=>drop.classList.remove('drag'));
drop.addEventListener('drop',e=>{
  e.preventDefault();drop.classList.remove('drag');
  const f = e.dataTransfer.files[0];
  if(!f){toast('No file');return}
  DATASETS.push({id:'ds'+Date.now(),name:f.name,tag:'new',kind:'force',rows:'—',dur:'—',hz:'—',
    cols:[{name:'col_0',mapped:'—',unit:'?'},{name:'col_1',mapped:'—',unit:'?'}],active:false});
  renderDatasets();
  toast('Uploaded '+f.name+' — Claude is sniffing columns…');
});
drop.onclick=()=>toast('File picker stub — mock UI');

/* ============================================================
   Render — cells
   ============================================================ */
function renderCells(){
  cellsEl.innerHTML = '';
  cells.forEach((c,i)=>{
    if(i===0) cellsEl.appendChild(addSlot(0));
    cellsEl.appendChild(buildCell(c,i));
    cellsEl.appendChild(addSlot(i+1));
  });
  mCells.textContent = cells.length;
  renderLlmCtx();
}

function buildCell(c,i){
  const el = document.createElement('div');
  el.className = 'cell '+c.type;
  el.draggable = true;
  el.dataset.id = c.id;
  el.dataset.idx = i;
  el.innerHTML = `
    <div class="cell-head">
      <span class="cell-handle" title="Drag to reorder"><svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><circle cx="8" cy="6" r="1.6"/><circle cx="16" cy="6" r="1.6"/><circle cx="8" cy="12" r="1.6"/><circle cx="16" cy="12" r="1.6"/><circle cx="8" cy="18" r="1.6"/><circle cx="16" cy="18" r="1.6"/></svg></span>
      <span class="cell-idx">c${i+1}</span>
      <span class="cell-ey">${cellEy(c)}</span>
      <span class="cell-title" contenteditable="true" spellcheck="false">${cellTitle(c)}</span>
      ${cellSubHtml(c)}
      <span class="cell-tools">
        ${c.type==='graph'?`<button class="cell-tool" data-act="focus" title="Expand (F)"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg></button>`:''}
        <button class="cell-tool" data-act="dup" title="Duplicate"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
        <button class="cell-tool danger" data-act="del" title="Delete"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg></button>
      </span>
    </div>
    ${cellBody(c,i)}
  `;
  wireCell(el,c,i);
  return el;
}

function cellEy(c){
  if(c.type==='graph') return GRAPH_TPLS[c.graph].ey;
  if(c.type==='stat')  return 'Stat · '+STAT_OPS[c.op].label;
  if(c.type==='llm')   return 'Ask Claude';
}
function cellTitle(c){
  if(c.type==='graph') return GRAPH_TPLS[c.graph].title;
  if(c.type==='stat')  return STAT_OPS[c.op].label+' — '+(c.inputs.a||'')+' vs '+(c.inputs.b||'');
  if(c.type==='llm')   return 'Asymmetry root-cause analysis';
}
function cellSubHtml(c){
  if(c.type==='graph'){
    const ds = DATASETS.find(d=>d.id===GRAPH_TPLS[c.graph].ds);
    return `<span class="ds-chip ${ds.tag}">${ds.name}</span>`;
  }
  if(c.type==='stat'){
    return (c.dsIds||[]).map(id=>{
      const ds = DATASETS.find(d=>d.id===id);
      return `<span class="ds-chip ${ds.tag}">${ds.name}</span>`;
    }).join(' ');
  }
  if(c.type==='llm'){
    return `<span class="cell-sub">from ${(c.refs||[]).join(', ')}</span>`;
  }
}

function cellBody(c,i){
  if(c.type==='graph') return graphBody(c);
  if(c.type==='stat')  return statBody(c,i);
  if(c.type==='llm')   return llmBody(c,i);
  return '';
}

/* ---- Graph ---- */
function graphBody(c){
  // Stride-avg toggle: if enabled on a 'force' graph, switch to the 'force_avg' template live.
  const activeKey = (c.strideAvg && c.graph==='force' && GRAPH_TPLS.force_avg) ? 'force_avg' : c.graph;
  const t = GRAPH_TPLS[activeKey];
  const preset = c.preset || 'ieee';
  const P = (typeof JOURNAL_PRESETS !== 'undefined') ? JOURNAL_PRESETS[preset] : null;
  const presetOpts = P ? Object.entries(JOURNAL_PRESETS).map(([k,v])=>
    `<option value="${k}" ${k===preset?'selected':''}>${v.name}</option>`).join('') : '';
  const canToggleAvg = (c.graph==='force' || c.graph==='force_avg');
  const fmts = (P && P.formats) ? P.formats : ['PDF','SVG','PNG'];
  const widthMm = P ? P.col2.w : null;
  const bodyPt  = P ? P.sizes.body : null;
  const dpi     = P ? P.dpi : null;
  return `
    <div class="graph-toolbar">
      ${P ? `<label class="gt-field"><span class="gt-lbl">Journal</span>
        <select class="gt-sel" data-graph-act="preset">${presetOpts}</select>
      </label>` : ''}
      ${canToggleAvg ? `<label class="gt-toggle"><input type="checkbox" data-graph-act="stride-avg" ${c.strideAvg?'checked':''}/><span>Stride avg ±SD</span></label>` : ''}
      <div class="gt-spacer"></div>
      ${P ? `<span class="gt-meta">${widthMm}mm · ${bodyPt}pt · ${dpi}dpi</span>` : ''}
      <div class="gt-export">
        <button class="gt-btn" data-graph-act="export">Export ▾</button>
        <div class="gt-menu" hidden>
          ${fmts.map(f=>`<button class="gt-mitem" data-graph-act="export-do" data-fmt="${f}">${f}</button>`).join('')}
        </div>
      </div>
    </div>
    <div class="plot">${renderPlotSvg(t)}</div>
    <div class="cell-legend">${(t.paths||[]).map(p=>{
      const dash = !!p.dash;
      return `<span class="lg-item"><span class="lg-sw ${dash?'dash':''}" style="${dash?`color:${p.c}`:`background:${p.c}`}"></span>${p.label}</span>`;
    }).join('')}</div>
    <div class="cell-meta">${(t.summary||[]).map(([k,v])=>`<span>${k}${v?' <b>'+v+'</b>':''}</span>`).join('')}</div>
  `;
}

function renderPlotSvg(t){
  // Bands: close upper and lower paths to the baseline (y=200), fill with evenodd
  // so the region BETWEEN upper and lower is filled (lower-closed overlaps & cancels upper's inner region).
  const bands = (t.bands||[]).map(b=>{
    const upperClosed = b.upper + ' L408,200 L48,200 Z';
    const lowerClosed = b.lower + ' L408,200 L48,200 Z';
    return `<path d="${upperClosed} ${lowerClosed}" fill="${b.c}" fill-opacity="${b.opacity}" fill-rule="evenodd" stroke="none"/>`;
  }).join('');
  const hlines = (t.hlines||[]).map(h=>{
    // y maps: 0..180 inverse: we keep given y
    return `<line x1="48" y1="${h.y}" x2="408" y2="${h.y}" stroke="${h.c}" stroke-width="0.8" stroke-dasharray="${h.dash||''}"/><text x="400" y="${h.y-3}" text-anchor="end" font-size="9" fill="${h.c}">${h.label||''}</text>`;
  }).join('');
  const boxes = (t.boxes||[]).map(b=>{
    // box from q1..q3, median line, whiskers min..max
    const bw = 36;
    return `<g>
      <line x1="${b.x}" y1="${b.max}" x2="${b.x}" y2="${b.min}" stroke="${b.c}" stroke-width="1.2"/>
      <line x1="${b.x-10}" y1="${b.min}" x2="${b.x+10}" y2="${b.min}" stroke="${b.c}" stroke-width="1.2"/>
      <line x1="${b.x-10}" y1="${b.max}" x2="${b.x+10}" y2="${b.max}" stroke="${b.c}" stroke-width="1.2"/>
      <rect x="${b.x-bw/2}" y="${b.q3}" width="${bw}" height="${b.q1-b.q3}" fill="${b.c}" fill-opacity=".2" stroke="${b.c}" stroke-width="1.2"/>
      <line x1="${b.x-bw/2}" y1="${b.med}" x2="${b.x+bw/2}" y2="${b.med}" stroke="${b.c}" stroke-width="2"/>
      <text x="${b.x}" y="198" text-anchor="middle" font-size="10" fill="#E2E8F0" font-weight="600">${b.label}</text>
    </g>`;
  }).join('');
  const bars = (t.bars||[]).map(b=>{
    const y = 180 - b.h;
    return `<g>
      <rect x="${b.x}" y="${y}" width="${b.w}" height="${b.h}" fill="${b.c}" fill-opacity=".85"/>
      <text x="${b.x+b.w/2}" y="198" text-anchor="middle" font-size="10" fill="#E2E8F0">${b.label}</text>
    </g>`;
  }).join('');
  const paths = (t.paths||[]).map(p=>`<path d="${p.d}" stroke="${p.c}" stroke-width="${p.w}" ${p.dash?`stroke-dasharray="${p.dash}"`:''} fill="none" stroke-linecap="round"/>`).join('');
  const yT = t.yTicks.map((x,i)=>`<text x="43" y="${23+i*40}">${x}</text>`).join('');
  const xT = t.xTicks.map((x,i)=>`<text x="${48+i*90}" y="194">${x}</text>`).join('');
  return `<svg viewBox="0 0 420 210" preserveAspectRatio="none">
    <g class="grid-line">
      <line x1="48" y1="23" x2="408" y2="23"/>
      <line x1="48" y1="63" x2="408" y2="63"/>
      <line x1="48" y1="103" x2="408" y2="103"/>
      <line x1="48" y1="143" x2="408" y2="143"/>
    </g>
    <line class="grid-line-major" x1="48" y1="180" x2="408" y2="180"/>
    <line class="axis-line" x1="48" y1="16" x2="48" y2="180"/>
    <line class="axis-line" x1="48" y1="180" x2="408" y2="180"/>
    <g class="tick-label" text-anchor="end">${yT}</g>
    <g class="tick-label" text-anchor="middle">${xT}</g>
    <text class="axis-title" x="228" y="206" text-anchor="middle">${t.xUnit}</text>
    <text class="axis-title" x="14" y="100" text-anchor="middle" transform="rotate(-90 14 100)">${t.yUnit}</text>
    ${bands}${bars}${boxes}${hlines}${paths}
  </svg>`;
}

/* ---- Stat cell ---- */
function statBody(c,i){
  const op = STAT_OPS[c.op];
  const result = op.run(c.inputs);
  return `
    <div class="stat-body">
      <div class="stat-inputs">
        <div class="stat-row">
          <label>Test</label>
          <select data-stat="op">
            ${Object.entries(STAT_OPS).map(([k,v])=>`<option value="${k}" ${k===c.op?'selected':''}>${v.label}</option>`).join('')}
          </select>
        </div>
        <div class="stat-row">
          <label>Dataset</label>
          <select data-stat="ds">
            ${DATASETS.map(d=>`<option value="${d.id}" ${(c.dsIds||[]).includes(d.id)?'selected':''}>${d.name}</option>`).join('')}
          </select>
        </div>
        <div class="stat-row">
          <label>Group A</label>
          <input type="text" data-stat="a" value="${c.inputs.a||''}" placeholder="column or cell ref"/>
        </div>
        <div class="stat-row">
          <label>Group B</label>
          <input type="text" data-stat="b" value="${c.inputs.b||''}" placeholder="column or cell ref"/>
        </div>
        <div class="stat-row">
          <label>α</label>
          <div class="op">
            <button class="on">.05</button><button>.01</button><button>.001</button>
          </div>
          <span style="font:500 10px 'JetBrains Mono',monospace;color:#6B7280;margin-left:auto">two-tailed</span>
        </div>
        <div class="stat-row" style="margin-top:4px;gap:6px">
          <span style="font:600 10px 'Pretendard',sans-serif;color:#6B7280;letter-spacing:.12em;text-transform:uppercase">Reference</span>
          <span class="ref-chip" data-ref="c1">c1.L Actual</span>
          <span class="ref-chip" data-ref="c1">c1.R Actual</span>
        </div>
      </div>
      <div class="stat-output">
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font:700 9.5px/1 'Pretendard',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:#6B7280">Result</span>
          <div class="stat-fmt" style="margin-left:auto" data-fmt-group="${c.id}">
            <button class="${c.fmt==='apa'?'on':''}" data-fmt="apa">APA</button>
            <button class="${c.fmt==='ieee'?'on':''}" data-fmt="ieee">IEEE</button>
            <button class="${c.fmt==='plain'?'on':''}" data-fmt="plain">Plain</button>
          </div>
        </div>
        ${renderStatKV(result)}
        <div class="stat-apa">
          <button class="copy" data-copy-apa>COPY</button>
          ${formatReport(result, c.fmt||'apa')}
        </div>
      </div>
    </div>
  `;
}

function renderStatKV(r){
  const rows = [];
  const push=(k,v,sig=false)=>rows.push(`<div class="stat-val ${sig?'sig':''}"><span>${k}</span><b>${v}</b></div>`);
  for(const [k,v] of Object.entries(r)){
    if(k==='test'||k==='psig'||k==='effect') continue;
    if(k==='p') push('p-value', v+(r.psig?' *':''), !!r.psig);
    else push(k, v, false);
  }
  if(r.effect) push('effect', r.effect);
  return rows.join('');
}

/* ---- Report formatting ---- */
function formatReport(r, fmt){
  if(fmt==='ieee'){
    // IEEE-ish: "A paired t-test showed t(13) = 3.27, p = .006, d = 0.87."
    if(r.t) return `A <b>${r.test}</b> showed <b>t</b>(${r.df}) = ${r.t}, <b>p</b> = ${r.p}${r.psig?' (significant)':''}, Cohen's <b>d</b> = ${r.cohen_d}. Mean difference = ${r.mean_diff}, 95% CI ${r.ci95}.`;
    if(r.F) return `<b>${r.test}</b>: <b>F</b>(${r.df1},${r.df2}) = ${r.F}, <b>p</b> = ${r.p}${r.psig?' (significant)':''}, η² = ${r.eta2}. ${r.posthoc||''}`;
    if(r.r) return `<b>${r.test}</b>: <b>r</b>(${r.n-2}) = ${r.r}, <b>p</b> = ${r.p}${r.psig?' (significant)':''}, 95% CI ${r.ci95}.`;
    return `<b>${r.test}</b>, d = ${r.cohen_d}, 95% CI ${r.ci95}, ${r.effect} effect.`;
  }
  if(fmt==='plain'){
    if(r.t) return `Paired t-test: t=${r.t}, df=${r.df}, p=${r.p}, d=${r.cohen_d}. Δ=${r.mean_diff} ${r.ci95}.`;
    if(r.F) return `ANOVA: F(${r.df1},${r.df2})=${r.F}, p=${r.p}, η²=${r.eta2}. ${r.posthoc||''}`;
    if(r.r) return `Pearson r=${r.r}, n=${r.n}, p=${r.p}, ${r.ci95}.`;
    return `Cohen's d=${r.cohen_d}, ${r.ci95}, ${r.effect}.`;
  }
  // APA default
  if(r.t) return `A paired-samples <i>t</i>-test indicated that the L/R peak force difference was statistically significant, <b><i>t</i>(${r.df}) = ${r.t}, <i>p</i> = ${r.p}</b>. Cohen's <i>d</i> = <b>${r.cohen_d}</b> (${r.effect} effect); mean difference = <b>${r.mean_diff}</b>, 95% CI ${r.ci95}.`;
  if(r.F) return `A one-way ANOVA revealed a significant effect of trial on force output, <b><i>F</i>(${r.df1}, ${r.df2}) = ${r.F}, <i>p</i> = ${r.p}, η² = ${r.eta2}</b> (${r.effect} effect). Post-hoc: ${r.posthoc||'—'}.`;
  if(r.r) return `A Pearson correlation indicated a ${r.effect} association between the two channels, <b><i>r</i>(${r.n-2}) = ${r.r}, <i>p</i> = ${r.p}</b>, 95% CI ${r.ci95}.`;
  return `Effect size (Cohen's <i>d</i>) = <b>${r.cohen_d}</b>, 95% CI ${r.ci95}, indicating a ${r.effect} effect.`;
}

/* ---- LLM cell ---- */
function llmBody(c,i){
  const resp = c.answer;
  const refChips = (c.refs||[]).map(r=>`<span class="ref-chip" data-ref="${r}">${r}</span>`).join('');
  return `
    <div class="llm-prompt">
      <span class="quoteb">PROMPT</span>
      <div style="flex:1">
        <div contenteditable="true" spellcheck="false">${c.prompt}</div>
        <div class="refs">${refChips}</div>
      </div>
    </div>
    <div class="llm-response">
      ${resp.text.map(p=>`<p>${p}</p>`).join('')}
    </div>
    <div class="llm-spawns">
      ${resp.spawns.map(s=>`<button class="llm-spawn" data-spawn="${s.action}">${s.label}</button>`).join('')}
    </div>
  `;
}

/* ============================================================
   Wire cell interactions
   ============================================================ */
function wireCell(el, c, i){
  el.querySelector('[data-act="dup"]')?.addEventListener('click',()=>{
    cells.splice(i+1,0,JSON.parse(JSON.stringify({...c, id:'c'+Date.now()})));
    renderCells();toast('Duplicated');
  });
  el.querySelector('[data-act="del"]')?.addEventListener('click',()=>{
    cells = cells.filter(x=>x.id!==c.id); renderCells(); toast('Removed');
  });
  el.querySelector('[data-act="focus"]')?.addEventListener('click',()=>openFocus(i));
  el.querySelector('.plot')?.addEventListener('dblclick',()=>openFocus(i));

  // Graph toolbar (preset / stride-avg / export)
  el.querySelector('[data-graph-act="preset"]')?.addEventListener('change',e=>{
    c.preset = e.target.value;
    renderCells();
    const P = JOURNAL_PRESETS[c.preset];
    toast(`Preset → ${P.name} · ${P.col2.w}mm · ${P.sizes.body}pt`);
  });
  el.querySelector('[data-graph-act="stride-avg"]')?.addEventListener('change',e=>{
    c.strideAvg = e.target.checked;
    renderCells();
    toast(c.strideAvg?'Stride avg ±SD ON (n=14)':'Raw waveform');
  });
  const expBtn = el.querySelector('[data-graph-act="export"]');
  const expMenu = el.querySelector('.gt-menu');
  expBtn?.addEventListener('click',e=>{
    e.stopPropagation();
    const open = !expMenu.hasAttribute('hidden');
    document.querySelectorAll('.gt-menu').forEach(m=>m.setAttribute('hidden',''));
    if(!open) expMenu.removeAttribute('hidden');
  });
  el.querySelectorAll('[data-graph-act="export-do"]').forEach(b=>{
    b.addEventListener('click',()=>{
      const fmt = b.dataset.fmt;
      const P = JOURNAL_PRESETS[c.preset||'ieee'];
      expMenu.setAttribute('hidden','');
      toast(`Exporting ${fmt} @ ${P.dpi}dpi · ${P.col2.w}mm`);
    });
  });

  // Stat cell inputs
  el.querySelectorAll('[data-stat]').forEach(inp=>{
    inp.addEventListener('change',e=>{
      const k = inp.dataset.stat;
      if(k==='op')  c.op = inp.value;
      if(k==='ds')  c.dsIds = [inp.value];
      if(k==='a')   c.inputs.a = inp.value;
      if(k==='b')   c.inputs.b = inp.value;
      renderCells();
      toast('Recomputed — '+STAT_OPS[c.op].label);
    });
  });
  el.querySelectorAll(`[data-fmt-group="${c.id}"] button`).forEach(b=>{
    b.addEventListener('click',()=>{
      c.fmt = b.dataset.fmt;
      renderCells();
    });
  });
  el.querySelector('[data-copy-apa]')?.addEventListener('click',e=>{
    const txt = el.querySelector('.stat-apa').innerText.replace(/^COPY\s*/,'');
    navigator.clipboard?.writeText(txt);
    toast('Copied to clipboard');
  });
  // LLM spawns
  el.querySelectorAll('[data-spawn]').forEach(b=>{
    b.addEventListener('click',()=>{
      const a = b.dataset.spawn;
      if(a.startsWith('graph:')){
        cells.splice(i+1,0,{id:'c'+Date.now(),type:'graph',graph:a.split(':')[1]});
      } else if(a.startsWith('stat:')){
        cells.splice(i+1,0,{id:'c'+Date.now(),type:'stat',op:a.split(':')[1],inputs:{a:'Trial 1',b:'Trial 5'},dsIds:['ds3'],fmt:'apa'});
      }
      renderCells();
      toast('Claude spawned a new cell');
    });
  });
  // ref-chip hover highlights target
  el.querySelectorAll('.ref-chip').forEach(chip=>{
    chip.addEventListener('mouseenter',()=>{
      const targetIdx = cells.findIndex(x=>x.id===chip.dataset.ref);
      if(targetIdx<0) return;
      const tgt = cellsEl.querySelectorAll('.cell')[targetIdx];
      tgt?.classList.add('ref-target');
    });
    chip.addEventListener('mouseleave',()=>{
      cellsEl.querySelectorAll('.cell.ref-target').forEach(x=>x.classList.remove('ref-target'));
    });
    chip.addEventListener('click',()=>{
      const targetIdx = cells.findIndex(x=>x.id===chip.dataset.ref);
      if(targetIdx<0) return;
      cellsEl.querySelectorAll('.cell')[targetIdx]?.scrollIntoView({block:'center',behavior:'smooth'});
    });
  });
  // Drag/drop
  el.addEventListener('dragstart',e=>{el.classList.add('dragging');e.dataTransfer.setData('text/plain',c.id)});
  el.addEventListener('dragend',()=>el.classList.remove('dragging'));
}

/* ============================================================
   Add-slot menu between cells (choose Graph / Stat / LLM)
   ============================================================ */
function addSlot(idx){
  const slot = document.createElement('div');
  slot.className='add-slot';
  slot.innerHTML = `
    <button class="graph" data-t="graph">＋ Graph</button>
    <button class="stat" data-t="stat">＋ Stats</button>
    <button class="llm" data-t="llm">＋ Ask Claude</button>
  `;
  slot.querySelectorAll('button').forEach(b=>{
    b.onclick=()=>insertCellAt(idx, b.dataset.t);
  });
  slot.addEventListener('dragover',e=>{e.preventDefault();slot.style.opacity=1;slot.style.height='36px'});
  slot.addEventListener('dragleave',()=>{slot.style.opacity='';slot.style.height=''});
  slot.addEventListener('drop',e=>{
    e.preventDefault();
    const id = e.dataTransfer.getData('text/plain');
    const from = cells.findIndex(x=>x.id===id); if(from<0) return;
    const [moved] = cells.splice(from,1);
    const to = idx>from?idx-1:idx;
    cells.splice(to,0,moved);
    renderCells();toast('Moved');
  });
  return slot;
}

function insertCellAt(idx,type){
  let c;
  if(type==='graph') c = {id:'c'+Date.now(),type:'graph',graph:'force'};
  if(type==='stat')  c = {id:'c'+Date.now(),type:'stat',op:'ttest_paired',inputs:{a:'L Actual',b:'R Actual'},dsIds:['ds1'],fmt:'apa'};
  if(type==='llm')   c = {id:'c'+Date.now(),type:'llm',prompt:'Analyze recent cells and summarize key findings.',refs:cells.slice(-2).map(x=>x.id),answer:{
    text:['Claude is thinking…','(mock response — wire Haiku 4.5 here)'],
    spawns:[{label:'+ Graph',action:'graph:force:zoom'}]
  }};
  cells.splice(idx,0,c);
  renderCells();
  toast('Added '+type);
}

/* ============================================================
   LLM dock — context chips + send
   ============================================================ */
function renderLlmCtx(){
  const ctx = document.getElementById('llm-ctx');
  const activeDs = DATASETS.filter(d=>d.active).map(d=>`<span class="ds-chip ${d.tag}">${d.name}</span>`).join('');
  const cellCount = cells.length;
  ctx.innerHTML = `<span class="lbl">CTX</span> ${activeDs} <span class="ds-chip" style="background:rgba(167,139,250,.1);border-color:rgba(167,139,250,.3);color:#A78BFA">${cellCount} cells</span>`;
}

const llmQ = document.getElementById('llm-q');
document.getElementById('llm-send').onclick = sendLlm;
llmQ.addEventListener('keydown',e=>{ if(e.key==='Enter') sendLlm(); });

function sendLlm(){
  const q = llmQ.value.trim(); if(!q) return;
  toast('Claude is analyzing…');
  // append an LLM cell at the end with this prompt
  const c = {id:'c'+Date.now(),type:'llm',prompt:q,refs:cells.slice(-2).map(x=>x.id),answer:{
    text:[
      `Analyzing <b>${q}</b> across ${DATASETS.filter(d=>d.active).length} active dataset(s).`,
      'Preliminary finding: asymmetry concentrates in <b>mid-stance (30–55% GC)</b> with peak Δ of <b class="num">4.82 N</b> favoring the L-limb. Paired-t confirms significance (<code>p = .006</code>).',
      'Would you like me to (a) overlay desired trajectory or (b) run an ANOVA across trials 1–5?'
    ],
    spawns:[
      {label:'(a) + Graph overlay', action:'graph:force'},
      {label:'(b) + ANOVA c1–c5',   action:'stat:anova'},
    ]
  }};
  cells.push(c);
  renderCells();
  llmQ.value='';
  setTimeout(()=>cellsEl.lastElementChild?.scrollIntoView({block:'center',behavior:'smooth'}),80);
}

/* ============================================================
   Mode toggle
   ============================================================ */
document.querySelectorAll('#mode-toggle button').forEach(b=>{
  b.onclick=()=>{
    document.querySelectorAll('#mode-toggle button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    if(b.dataset.mode==='publication'){
      document.body.classList.add('pub');
      toast('Publication mode — plots switched to print palette, IEEE preset');
    } else {
      document.body.classList.remove('pub');
      toast('Quick mode');
    }
  };
});

/* ============================================================
   ⌘K palette
   ============================================================ */
const COMMANDS = [
  { group:'Add cell',   label:'Insert Graph · Force L/R',       hint:'⏎', action:()=>insertCellAt(cells.length,'graph') },
  { group:'Add cell',   label:'Insert Stats · Paired t-test',    hint:'⏎', action:()=>insertCellAt(cells.length,'stat') },
  { group:'Add cell',   label:'Insert LLM cell (Ask Claude)',    hint:'⏎', action:()=>insertCellAt(cells.length,'llm') },
  { group:'Stats',      label:'Paired t-test · L vs R',          hint:'',  action:()=>{insertCellAt(cells.length,'stat')} },
  { group:'Stats',      label:'One-way ANOVA · across trials',   hint:'',  action:()=>{insertCellAt(cells.length,'stat'); cells[cells.length-1].op='anova';cells[cells.length-1].dsIds=['ds3'];renderCells()} },
  { group:'Stats',      label:'Pearson correlation · L × R',     hint:'',  action:()=>{insertCellAt(cells.length,'stat'); cells[cells.length-1].op='corr';renderCells()} },
  { group:'Stats',      label:'Cohen\'s d · effect size',        hint:'',  action:()=>{insertCellAt(cells.length,'stat'); cells[cells.length-1].op='cohen';renderCells()} },
  { group:'Export',     label:'Export page as SVG bundle',       hint:'⇧⌘E', action:()=>toast('Exported '+cells.filter(c=>c.type==='graph').length+' plots as SVG bundle') },
  { group:'Export',     label:'Export for IEEE preset (88mm)',   hint:'',  action:()=>toast('IEEE preset → svg, pdf · 88mm column') },
  { group:'Export',     label:'Export for Nature preset (89mm)', hint:'',  action:()=>toast('Nature preset → svg, pdf · 89mm column') },
  { group:'Export',     label:'Export stats as APA .docx',       hint:'',  action:()=>toast('Stats → publication_stats.docx (4 results)') },
  { group:'Mode',       label:'Toggle Publication mode',         hint:'⌘P', action:()=>{document.querySelector('#mode-toggle button:not(.on)')?.click()} },
];

const cmdk = document.getElementById('cmdk');
const cmdkList = document.getElementById('cmdk-list');
const cmdkQ = document.getElementById('cmdk-q');
document.getElementById('cmdk-trigger').onclick=()=>openCmdK();

function openCmdK(seed){cmdk.classList.add('open');cmdkQ.value=seed||'';cmdkQ.focus();renderCmdK()}
function closeCmdK(){cmdk.classList.remove('open')}
function renderCmdK(){
  const q = cmdkQ.value.trim().toLowerCase();
  const filtered = q?COMMANDS.filter(c=>c.label.toLowerCase().includes(q)||c.group.toLowerCase().includes(q)):COMMANDS;
  const byGroup={}; filtered.forEach(c=>{(byGroup[c.group]=byGroup[c.group]||[]).push(c)});
  let html = '';
  if(!filtered.length) html = `<div style="padding:28px 20px;color:#6B7280;font:500 12px sans-serif;text-align:center">No match. <b style="color:#F09708">⏎</b> to ask Claude directly.</div>`;
  let gi=0;
  for(const g in byGroup){
    html += `<div class="cmdk-section">${g}</div>`;
    byGroup[g].forEach((c,i)=>{
      const active = gi===0&&i===0?'true':'false';
      html += `<div class="cmdk-item" data-active="${active}" data-cmd="${COMMANDS.indexOf(c)}">
        <span class="cmdk-icon">›</span><span>${c.label}</span><span class="cmdk-meta">${c.hint||''}</span></div>`;
    });
    gi++;
  }
  cmdkList.innerHTML = html;
  cmdkList.querySelectorAll('.cmdk-item').forEach(el=>{
    el.onclick=()=>{COMMANDS[+el.dataset.cmd].action();closeCmdK()};
  });
}
cmdkQ.addEventListener('input',renderCmdK);
cmdkQ.addEventListener('keydown',e=>{
  if(e.key==='Enter'){
    const a=cmdkList.querySelector('[data-active="true"]')||cmdkList.querySelector('.cmdk-item');
    if(a){COMMANDS[+a.dataset.cmd].action();closeCmdK()}
    else if(cmdkQ.value.trim()){toast('Claude: "'+cmdkQ.value+'"…');setTimeout(()=>{llmQ.value=cmdkQ.value;sendLlm()},300);closeCmdK()}
  }
  if(e.key==='ArrowDown'||e.key==='ArrowUp'){
    e.preventDefault();
    const items=[...cmdkList.querySelectorAll('.cmdk-item')];
    const cur=items.findIndex(el=>el.dataset.active==='true');
    items.forEach(el=>el.dataset.active='false');
    const n = e.key==='ArrowDown'?(cur+1)%items.length:(cur-1+items.length)%items.length;
    if(items[n]) items[n].dataset.active='true';
  }
});
document.addEventListener('keydown',e=>{
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCmdK()}
  if(e.key==='Escape'){closeCmdK();closeFocus()}
});
cmdk.addEventListener('click',e=>{if(e.target===cmdk)closeCmdK()});

/* ============================================================
   Toast
   ============================================================ */
let toastTimer;
function toast(msg){
  const t=document.getElementById('toast');
  t.textContent=msg;t.classList.add('on');
  clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('on'),2400);
}

/* ============================================================
   Focus modal (graph zoom)
   ============================================================ */
const focus=document.getElementById('focus');
const fPlotWrap=document.getElementById('f-plotwrap');
const fPlot=document.getElementById('f-plot');
const fCoord=document.getElementById('f-coord');
let focusIdx=-1;
let focusState={xDomain:[0,100],seriesHidden:new Set(),crosshair:true,grid:true};

function openFocus(idx){
  // find nearest graph cell
  if(cells[idx]?.type!=='graph'){
    const g = cells.findIndex((c,i)=>i>=idx && c.type==='graph');
    if(g<0){ toast('No graph cell to focus'); return; }
    idx = g;
  }
  focusIdx=idx;
  focusState.xDomain=[0,100];focusState.seriesHidden=new Set();
  renderFocus();
  focus.classList.add('open');
  document.body.classList.add('focused');
  document.body.style.overflow='hidden';
}
function closeFocus(){
  focus.classList.remove('open');
  document.body.classList.remove('focused');
  document.body.style.overflow='';
  focusIdx=-1;
}

function renderFocus(){
  if(focusIdx<0) return;
  const c = cells[focusIdx];
  const t = GRAPH_TPLS[c.graph];
  document.getElementById('f-ey').textContent=t.ey;
  document.getElementById('f-title').textContent=t.title;
  const ds = DATASETS.find(d=>d.id===t.ds);
  document.getElementById('f-sub').textContent=ds.name+' · '+ds.rows.toLocaleString()+' rows';
  // navigate only among graph cells
  const graphCells = cells.map((c,i)=>({c,i})).filter(x=>x.c.type==='graph');
  const posInGraphs = graphCells.findIndex(x=>x.i===focusIdx);
  document.getElementById('f-count').textContent=(posInGraphs+1)+' / '+graphCells.length;

  const [x0,x1] = focusState.xDomain;
  const clipX=48+(360*x0/100), clipW=360*(x1-x0)/100;
  const paths = t.paths.map((p,i)=>{
    if(focusState.seriesHidden.has(i)) return '';
    return `<path d="${p.d}" stroke="${p.c}" stroke-width="${p.w+0.6}" ${p.dash?`stroke-dasharray="${p.dash}"`:''} fill="none" stroke-linecap="round" clip-path="url(#fClip)"/>`;
  }).join('');
  const xVals=[]; const d0=parseFloat(t.xTicks[0]), d1=parseFloat(t.xTicks[t.xTicks.length-1]);
  for(let k=0;k<5;k++){const tn=x0+(x1-x0)*k/4;xVals.push((d0+(d1-d0)*tn/100).toFixed(1).replace(/\.0$/,''))}
  const xT=xVals.map((x,k)=>`<text x="${48+k*90}" y="194">${x}</text>`).join('');
  const yT=t.yTicks.map((x,k)=>`<text x="43" y="${23+k*40}">${x}</text>`).join('');
  const gridLines=focusState.grid?`
    <line x1="48" y1="23" x2="408" y2="23"/>
    <line x1="48" y1="63" x2="408" y2="63"/>
    <line x1="48" y1="103" x2="408" y2="103"/>
    <line x1="48" y1="143" x2="408" y2="143"/>
    <line x1="138" y1="16" x2="138" y2="180"/>
    <line x1="228" y1="16" x2="228" y2="180"/>
    <line x1="318" y1="16" x2="318" y2="180"/>`:'';
  fPlot.innerHTML = `<svg viewBox="0 0 420 210" preserveAspectRatio="none">
    <defs><clipPath id="fClip"><rect x="${clipX}" y="16" width="${clipW}" height="166"/></clipPath></defs>
    <g class="grid-line">${gridLines}</g>
    <line class="grid-line-major" x1="48" y1="180" x2="408" y2="180"/>
    <line class="axis-line" x1="48" y1="16" x2="48" y2="180"/>
    <line class="axis-line" x1="48" y1="180" x2="408" y2="180"/>
    <g class="tick-label" text-anchor="end">${yT}</g>
    <g class="tick-label" text-anchor="middle">${xT}</g>
    <text class="axis-title" x="228" y="206" text-anchor="middle">${t.xUnit}</text>
    <text class="axis-title" x="14" y="100" text-anchor="middle" transform="rotate(-90 14 100)">${t.yUnit}</text>
    ${paths}
    <g><line class="crosshair-v" x1="0" y1="16" x2="0" y2="180"/>
       <line class="crosshair-h" x1="48" y1="0" x2="408" y2="0"/>
       <rect class="brush" x="0" y="16" width="0" height="164"/></g></svg>`;
  document.getElementById('f-stats').innerHTML =
    t.summary.map(([k,v])=>`<div class="fs-stat"><span>${k}</span><b>${v||'—'}</b></div>`).join('') +
    `<div class="fs-stat" style="color:${COLORS.accent}"><span>x-range</span><b>${xVals[0]} — ${xVals[4]}</b></div>`;
  document.getElementById('f-series').innerHTML = t.paths.map((p,i)=>{
    const off=focusState.seriesHidden.has(i);
    const sw=p.dash?`background-image:linear-gradient(to right,${p.c} 55%,transparent 55%);background-size:4px 100%;border-color:${p.c}`:`background:${p.c};border-color:${p.c}`;
    return `<div class="fs-series ${off?'off':''}" data-i="${i}">
      <span class="tog" style="${off?'':sw}">${off?'':'✓'}</span><span>${p.label}</span><span class="val">${p.dash?'desired':'actual'}</span></div>`;
  }).join('');
  document.querySelectorAll('#f-series .fs-series').forEach(el=>{
    el.onclick=()=>{const i=+el.dataset.i;if(focusState.seriesHidden.has(i))focusState.seriesHidden.delete(i);else focusState.seriesHidden.add(i);renderFocus()};
  });
}

(function wireFocus(){
  let brushStart=null;
  fPlotWrap.addEventListener('mouseenter',()=>{if(focusState.crosshair) fPlotWrap.classList.add('hovering')});
  fPlotWrap.addEventListener('mouseleave',()=>{fPlotWrap.classList.remove('hovering');fPlotWrap.classList.remove('brushing');brushStart=null});
  fPlotWrap.addEventListener('mousemove',e=>{
    const svg=fPlot.querySelector('svg');if(!svg)return;
    const r=svg.getBoundingClientRect();
    const vx=((e.clientX-r.left)/r.width)*420, vy=((e.clientY-r.top)/r.height)*210;
    const t=GRAPH_TPLS[cells[focusIdx].graph], [x0,x1]=focusState.xDomain;
    const tn=Math.max(0,Math.min(1,(vx-48)/360));
    const xD=parseFloat(t.xTicks[0])+(parseFloat(t.xTicks[t.xTicks.length-1])-parseFloat(t.xTicks[0]))*(x0/100+tn*(x1-x0)/100);
    const yF=parseFloat(t.yTicks[0]), yL=parseFloat(t.yTicks[t.yTicks.length-1]);
    const yn=Math.max(0,Math.min(1,(vy-16)/164));
    const yD=yF+(yL-yF)*yn;
    fCoord.innerHTML=`${t.xUnit.split(' ')[0]}: <b>${xD.toFixed(1)}</b> · ${t.yUnit.split(' ')[0]}: <b class="mint">${yD.toFixed(1)}</b>`;
    const v=svg.querySelector('.crosshair-v'),h=svg.querySelector('.crosshair-h');
    if(v&&h){v.setAttribute('x1',vx);v.setAttribute('x2',vx);h.setAttribute('y1',vy);h.setAttribute('y2',vy)}
    if(brushStart){const x=Math.min(brushStart.vx,vx), w=Math.abs(vx-brushStart.vx);
      const b=svg.querySelector('.brush');b.setAttribute('x',x);b.setAttribute('width',w)}
  });
  fPlotWrap.addEventListener('mousedown',e=>{
    const svg=fPlot.querySelector('svg');if(!svg)return;
    const r=svg.getBoundingClientRect();
    const vx=((e.clientX-r.left)/r.width)*420;
    if(vx<48||vx>408)return;
    brushStart={vx};fPlotWrap.classList.add('brushing');
  });
  fPlotWrap.addEventListener('mouseup',e=>{
    if(!brushStart){fPlotWrap.classList.remove('brushing');return}
    const svg=fPlot.querySelector('svg'), r=svg.getBoundingClientRect();
    const vx=Math.max(48,Math.min(408,((e.clientX-r.left)/r.width)*420));
    const a=Math.min(brushStart.vx,vx), b=Math.max(brushStart.vx,vx);
    fPlotWrap.classList.remove('brushing');brushStart=null;
    if(b-a<6) return;
    const [x0,x1]=focusState.xDomain, span=x1-x0;
    focusState.xDomain=[Math.max(0,x0+span*(a-48)/360),Math.min(100,x0+span*(b-48)/360)];
    renderFocus();
    toast('Zoomed to '+focusState.xDomain.map(v=>v.toFixed(0)+'%').join('–'));
  });
})();

document.querySelectorAll('.focus-toolbar .ftb-btn').forEach(b=>{
  b.onclick=()=>{
    const t=b.dataset.tool;
    if(t==='reset'){focusState.xDomain=[0,100];focusState.seriesHidden=new Set();renderFocus();toast('Reset')}
    else if(t==='crosshair'){focusState.crosshair=!focusState.crosshair;b.classList.toggle('on',focusState.crosshair);if(!focusState.crosshair)fPlotWrap.classList.remove('hovering')}
    else if(t==='grid'){focusState.grid=!focusState.grid;b.classList.toggle('on',focusState.grid);renderFocus()}
    else if(t==='download'){toast('Exported '+GRAPH_TPLS[cells[focusIdx].graph].title+'.svg')}
    else if(t==='download-pdf'){toast('Exported '+GRAPH_TPLS[cells[focusIdx].graph].title+'.pdf · vector')}
    else if(t==='brush'){toast('Drag across the plot to zoom')}
  };
});
document.querySelectorAll('#f-preset button').forEach(b=>{
  b.onclick=()=>{
    const p=b.dataset.preset;
    document.querySelectorAll('#f-preset button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    toast({ieee:'IEEE preset · 88mm column, Times 8pt',nature:'Nature preset · 89mm column, Helvetica 8pt',apa:'APA preset · 6in, Times 10pt'}[p]);
  };
});

document.getElementById('f-prev').onclick=()=>{
  const graphs=cells.map((c,i)=>({c,i})).filter(x=>x.c.type==='graph');
  const pos=graphs.findIndex(x=>x.i===focusIdx);
  if(pos>0){focusIdx=graphs[pos-1].i;focusState.xDomain=[0,100];focusState.seriesHidden=new Set();renderFocus()}
};
document.getElementById('f-next').onclick=()=>{
  const graphs=cells.map((c,i)=>({c,i})).filter(x=>x.c.type==='graph');
  const pos=graphs.findIndex(x=>x.i===focusIdx);
  if(pos<graphs.length-1){focusIdx=graphs[pos+1].i;focusState.xDomain=[0,100];focusState.seriesHidden=new Set();renderFocus()}
};
document.getElementById('f-close').onclick=closeFocus;
focus.addEventListener('click',e=>{if(e.target===focus) closeFocus()});
document.getElementById('f-ask').addEventListener('keydown',e=>{
  if(e.key==='Enter'&&e.target.value.trim()){
    toast('Claude thinking…');
    setTimeout(()=>toast('Claude: peak Δ in window = 4.8 N — see sidebar'),900);
    e.target.value='';
  }
});
document.getElementById('f-send').onclick=()=>{
  const i=document.getElementById('f-ask');
  if(i.value.trim()){toast('Claude thinking…');setTimeout(()=>toast('Claude: see sidebar'),900);i.value=''}
};

document.addEventListener('keydown',e=>{
  if(!focus.classList.contains('open')) return;
  if(e.key==='ArrowLeft')  document.getElementById('f-prev').click();
  if(e.key==='ArrowRight') document.getElementById('f-next').click();
  if(e.key.toLowerCase()==='f') closeFocus();
});
document.addEventListener('keydown',e=>{
  if(focus.classList.contains('open'))return;
  if(cmdk.classList.contains('open'))return;
  const tag=(e.target.tagName||'').toLowerCase();
  if(tag==='input'||tag==='textarea'||e.target.isContentEditable) return;
  if(e.key.toLowerCase()==='f'){
    const g=cells.findIndex(c=>c.type==='graph'); if(g>=0) openFocus(g);
  }
});

/* ============================================================
   Boot
   ============================================================ */
renderDatasets();
renderCells();

const titleEl=document.querySelector('.page-title');
titleEl.textContent=localStorage.getItem('hw_page_title')||titleEl.textContent;
titleEl.addEventListener('input',()=>localStorage.setItem('hw_page_title',titleEl.textContent));

