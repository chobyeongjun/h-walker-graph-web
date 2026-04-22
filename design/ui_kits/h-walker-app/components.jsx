// H-Walker UI Kit — small components
// Stroke-2 Feather/Lucide-style icons, currentColor everywhere.

const Icon = ({ d, size = 16, sw = 2 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
       strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round"
       dangerouslySetInnerHTML={{ __html: d }} />
);

const I = {
  zap:    <Icon d='<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>' sw={2.5}/>,
  folder: <Icon d='<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>'/>,
  file:   <Icon d='<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>' sw={1.8}/>,
  msg:    <Icon d='<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'/>,
  send:   <Icon d='<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>' sw={2.5}/>,
  search: <Icon d='<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'/>,
  upload: <Icon d='<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>'/>,
  chev:   <Icon d='<polyline points="9 18 15 12 9 6"/>' sw={3} size={10}/>,
  plus:   <Icon d='<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>' sw={3}/>,
  x:      <Icon d='<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>' sw={2.5}/>,
  copy:   <Icon d='<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'/>,
  dl:     <Icon d='<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>'/>,
  chart:  <Icon d='<path d="M3 3v18h18"/><path d="M7 16l4-6 4 4 5-8"/>'/>,
};

const Logo = ({ size = 32 }) => (
  <div style={{width:size,height:size,borderRadius:9,background:'linear-gradient(135deg,#F09708,#FFB347)',
               display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',
               boxShadow:'0 0 15px rgba(240,151,8,0.3)'}}>
    <svg width={size*0.55} height={size*0.55} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  </div>
);

const Eyebrow = ({ children, tone = "gray" }) => {
  const colors = { gray: "#9CA3AF", accent: "#F09708", mint: "#00FFB2", white: "#fff" };
  return <span style={{font:"700 11px/1 Pretendard,'Apple SD Gothic Neo',sans-serif",letterSpacing:".2em",textTransform:"uppercase",color:colors[tone]}}>{children}</span>;
};

const LiveDot = ({ color = "#00FFB2" }) => (
  <span style={{width:8,height:8,borderRadius:"50%",background:color,boxShadow:`0 0 10px ${color}`,animation:"hwPulse 2s ease-in-out infinite",display:"inline-block"}}/>
);

const Chip = ({ children, tone = "orange" }) => {
  const t = tone === "mint"
    ? {bg:"rgba(0,255,178,.1)",bd:"rgba(0,255,178,.25)",fg:"#00FFB2"}
    : {bg:"rgba(240,151,8,.1)",bd:"rgba(240,151,8,.2)",fg:"#F09708"};
  return <span style={{background:t.bg,border:`1px solid ${t.bd}`,color:t.fg,padding:"3px 8px",borderRadius:6,font:"500 10px Pretendard,'Apple SD Gothic Neo',sans-serif"}}>{children}</span>;
};

const PrimaryBtn = ({ children, onClick, disabled, icon }) => (
  <button onClick={onClick} disabled={disabled}
    style={{display:"inline-flex",alignItems:"center",justifyContent:"center",gap:8,
      background:disabled?"#1f2937":"#F09708",color:disabled?"#4b5563":"#fff",
      font:"700 13px/1 Pretendard,'Apple SD Gothic Neo',sans-serif",letterSpacing:"-0.01em",textTransform:"uppercase",
      padding:"12px 16px",borderRadius:12,border:0,cursor:disabled?"not-allowed":"pointer",
      boxShadow:disabled?"none":"0 0 15px rgba(240,151,8,.2)",transition:"all .2s"}}
    onMouseEnter={e=>!disabled&&(e.currentTarget.style.boxShadow="0 0 25px rgba(240,151,8,.4)",e.currentTarget.style.background="#D68607")}
    onMouseLeave={e=>!disabled&&(e.currentTarget.style.boxShadow="0 0 15px rgba(240,151,8,.2)",e.currentTarget.style.background="#F09708")}>
    {icon}{children}
  </button>
);

const IconBtn = ({ icon, onClick, disabled, title }) => (
  <button onClick={onClick} disabled={disabled} title={title} aria-label={title}
    style={{background:disabled?"#1f2937":"#F09708",color:"#fff",border:0,padding:12,borderRadius:14,
      cursor:disabled?"not-allowed":"pointer",display:"inline-flex",boxShadow:disabled?"none":"0 0 15px rgba(240,151,8,.2)"}}>
    {icon}
  </button>
);

const GhostBtn = ({ children, onClick, icon }) => (
  <button onClick={onClick}
    style={{display:"inline-flex",alignItems:"center",gap:6,background:"rgba(23,27,94,.4)",
      color:"#E2E8F0",border:"1px solid rgba(255,255,255,.06)",padding:"8px 12px",
      borderRadius:10,font:"600 11px Pretendard,'Apple SD Gothic Neo',sans-serif",letterSpacing:".04em",cursor:"pointer",transition:"all .2s"}}
    onMouseEnter={e=>{e.currentTarget.style.background="rgba(23,27,94,.7)";e.currentTarget.style.color="#fff"}}
    onMouseLeave={e=>{e.currentTarget.style.background="rgba(23,27,94,.4)";e.currentTarget.style.color="#E2E8F0"}}>
    {icon}{children}
  </button>
);

// Top nav — matches App.tsx exactly
function TopNav({ mode, setMode }) {
  return (
    <nav style={{display:"flex",alignItems:"center",gap:8,padding:"10px 20px",
      background:"rgba(11,14,46,.9)",backdropFilter:"blur(24px)",
      borderBottom:"1px solid rgba(240,151,8,.15)",position:"relative",zIndex:10}}>
      <div style={{display:"flex",alignItems:"center",gap:12,marginRight:32}}>
        <Logo/>
        <div style={{display:"flex",flexDirection:"column",lineHeight:1.1}}>
          <span style={{font:"800 15px Pretendard,'Apple SD Gothic Neo',sans-serif",letterSpacing:"-0.01em",color:"#fff"}}>
            H-WALKER <span style={{color:"#F09708"}}>CORE</span>
          </span>
          <span style={{font:"600 10px Pretendard,'Apple SD Gothic Neo',sans-serif",color:"#6B7280",letterSpacing:".2em",textTransform:"uppercase"}}>Analysis Engine</span>
        </div>
      </div>
      <div style={{display:"flex",gap:4,background:"rgba(23,27,94,.4)",borderRadius:16,padding:4,border:"1px solid rgba(255,255,255,.05)"}}>
        {["quick","publication"].map(m=>(
          <button key={m} onClick={()=>setMode(m)}
            style={{padding:"6px 24px",borderRadius:12,border:0,cursor:"pointer",
              font:"700 11px Pretendard,'Apple SD Gothic Neo',sans-serif",letterSpacing:".08em",textTransform:"uppercase",
              background:mode===m?"#F09708":"transparent",
              color:mode===m?"#fff":"#9CA3AF",
              boxShadow:mode===m?"0 0 20px rgba(240,151,8,.4)":"none",transition:"all .3s"}}>
            {m}
          </button>
        ))}
      </div>
      <div style={{flex:1}}/>
      <div style={{display:"flex",alignItems:"center",gap:12,padding:"6px 12px",background:"rgba(23,27,94,.3)",
        borderRadius:12,border:"1px solid rgba(255,255,255,.05)"}}>
        <LiveDot/>
        <span style={{font:"700 11px JetBrains Mono,monospace",color:"#00FFB2",letterSpacing:".05em"}}>GEMMA 4:E4B</span>
      </div>
    </nav>
  );
}

Object.assign(window, { I, Logo, Eyebrow, LiveDot, Chip, PrimaryBtn, IconBtn, GhostBtn, TopNav, Icon });
