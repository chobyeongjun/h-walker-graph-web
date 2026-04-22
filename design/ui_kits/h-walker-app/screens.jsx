// H-Walker UI Kit — screens

function LegacyShell() {
  const [mode, setMode] = React.useState("quick");
  const [selected, setSelected] = React.useState("trial_2_imu.csv");
  const [input, setInput] = React.useState("");
  const [messages, setMessages] = React.useState([
    { role: "user", content: "오늘 실험 Force 비교해줘" },
    { role: "assistant", content: "Force 분석을 시작합니다. L/R_ActForce_N 컬럼에서 peak force와 보행 대칭성(Symmetry Index)을 계산 중입니다…" },
  ]);

  return (
    <div style={{display:"flex",flexDirection:"column",height:"100vh",background:"#0B0E2E",color:"#E2E8F0",font:"400 13px Pretendard,'Apple SD Gothic Neo',sans-serif"}}>
      <TopNav mode={mode} setMode={setMode}/>
      <div style={{display:"flex",flex:1,overflow:"hidden"}}>
        {/* Left panel */}
        <aside style={{width:240,background:"rgba(11,14,46,.9)",borderRight:"1px solid rgba(255,255,255,.05)",
          display:"flex",flexDirection:"column"}}>
          <div style={{padding:"14px 20px",borderBottom:"1px solid rgba(255,255,255,.05)",display:"flex",alignItems:"center",gap:10}}>
            <span style={{color:"#F09708"}}>{I.folder}</span>
            <Eyebrow>Drive Explorer</Eyebrow>
          </div>
          <div style={{margin:"12px 12px 8px",display:"flex",background:"rgba(23,27,94,.4)",borderRadius:10,padding:4,border:"1px solid rgba(255,255,255,.05)"}}>
            {["DRIVE","LOCAL"].map((t,i)=>(
              <button key={t} style={{flex:1,padding:"8px 0",border:0,borderRadius:8,cursor:"pointer",
                font:"700 10px Pretendard,'Apple SD Gothic Neo',sans-serif",letterSpacing:".1em",
                background:i===0?"#F09708":"transparent",color:i===0?"#fff":"#6B7280"}}>{t}</button>
            ))}
          </div>
          <div style={{padding:"0 10px",flex:1,overflow:"auto"}}>
            {["2026-04-15 trial","2026-04-08 pilot"].map((f,i)=>(
              <div key={f}>
                <div style={{display:"flex",alignItems:"center",gap:8,padding:"6px 10px",borderRadius:8,cursor:"pointer",color:"#E2E8F0"}}>
                  <span style={{color:"#6B7280",transform:i===0?"rotate(90deg)":"none",display:"inline-flex"}}>{I.chev}</span>
                  <span style={{color:"rgba(240,151,8,.8)"}}>{I.folder}</span>
                  <span style={{fontSize:12}}>{f}</span>
                </div>
                {i===0 && (
                  <div style={{marginLeft:16,borderLeft:"1px solid rgba(255,255,255,.05)",paddingLeft:4}}>
                    {["trial_1_force.csv","trial_2_imu.csv","gait_events.csv"].map(fn=>(
                      <div key={fn} onClick={()=>setSelected(fn)}
                        style={{display:"flex",alignItems:"center",gap:6,padding:"6px 10px",borderRadius:8,cursor:"pointer",
                          fontSize:12,color:selected===fn?"#fff":"#9CA3AF",
                          background:selected===fn?"rgba(240,151,8,.1)":"transparent"}}>
                        <span style={{color:selected===fn?"#F09708":"#6B7280"}}>{I.file}</span>
                        <span style={{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{fn}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          <div style={{padding:14,borderTop:"1px solid rgba(255,255,255,.05)",background:"rgba(255,255,255,.03)"}}>
            <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10}}>
              <LiveDot color="#F09708"/>
              <span style={{font:"700 11px Pretendard,'Apple SD Gothic Neo',sans-serif",color:"#E2E8F0",letterSpacing:".02em"}}>1 FILE SELECTED</span>
            </div>
            <div style={{width:"100%"}}><PrimaryBtn icon={I.zap}>Run Analysis</PrimaryBtn></div>
          </div>
        </aside>

        {/* Graph canvas */}
        <main style={{flex:1,display:"flex",alignItems:"center",justifyContent:"center",padding:20,overflow:"auto"}}>
          <div style={{display:"flex",flexDirection:"column",alignItems:"center",textAlign:"center"}}>
            <div style={{position:"relative",marginBottom:32}}>
              <div style={{width:96,height:96,borderRadius:32,background:"rgba(23,27,94,.2)",
                display:"flex",alignItems:"center",justifyContent:"center",border:"1px solid rgba(255,255,255,.05)",backdropFilter:"blur(8px)"}}>
                <span style={{color:"#374151"}}><Icon size={42} sw={1.8} d='<path d="M3 3v18h18"/><path d="M7 16l4-6 4 4 5-8" stroke="#F09708" stroke-opacity=".6"/>'/></span>
              </div>
              <div style={{position:"absolute",bottom:-8,right:-8,width:32,height:32,borderRadius:12,
                background:"rgba(240,151,8,.1)",border:"1px solid rgba(240,151,8,.2)",display:"flex",alignItems:"center",justifyContent:"center",color:"#F09708"}}>
                {I.plus}
              </div>
            </div>
            <p style={{font:"700 16px Pretendard,'Apple SD Gothic Neo',sans-serif",color:"#fff",margin:"0 0 8px"}}>H-WALKER 분석 준비 완료</p>
            <p style={{fontSize:12,color:"#6B7280",maxWidth:260,lineHeight:1.6,margin:"0 0 24px"}}>
              Google Drive에서 CSV 파일을 선택한 뒤<br/>AI 파트너에게 데이터 분석을 요청하세요
            </p>
            <div style={{display:"flex",alignItems:"center",gap:12,padding:"10px 16px",background:"rgba(255,255,255,.04)",
              border:"1px solid rgba(255,255,255,.05)",borderRadius:16,font:"400 11px JetBrains Mono,monospace",color:"#9CA3AF"}}>
              <span style={{color:"#F09708",fontWeight:700}}>&gt;</span>
              "오늘 걸음 데이터의 Force 비교해줘"
            </div>
          </div>
        </main>

        {/* AI panel */}
        <aside style={{width:320,background:"rgba(11,14,46,.9)",borderLeft:"1px solid rgba(255,255,255,.05)",
          display:"flex",flexDirection:"column"}}>
          <div style={{padding:"12px 16px",borderBottom:"1px solid rgba(255,255,255,.05)",display:"flex",alignItems:"center",gap:8}}>
            <div style={{width:22,height:22,borderRadius:8,background:"rgba(240,151,8,.1)",display:"flex",alignItems:"center",justifyContent:"center",color:"#F09708"}}>
              <Icon size={12} d='<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'/>
            </div>
            <Eyebrow>AI Partner</Eyebrow>
            <div style={{marginLeft:"auto",display:"flex",alignItems:"center",gap:6}}>
              <span style={{width:6,height:6,borderRadius:"50%",background:"#F09708",boxShadow:"0 0 8px #F09708"}}/>
              <span style={{font:"700 10px Pretendard,'Apple SD Gothic Neo',sans-serif",color:"#F09708",textTransform:"uppercase",letterSpacing:"-0.02em"}}>live</span>
            </div>
          </div>
          <div style={{flex:1,padding:12,display:"flex",flexDirection:"column",gap:10,overflow:"auto"}}>
            {messages.map((m,i)=>(
              <div key={i} style={{display:"flex",justifyContent:m.role==="user"?"flex-end":"flex-start"}}>
                <div style={{maxWidth:"88%",padding:"10px 14px",fontSize:13,lineHeight:1.5,
                  background:m.role==="user"?"linear-gradient(135deg,#171B5E,#0B0E2E)":"rgba(23,27,94,.3)",
                  color:m.role==="user"?"#fff":"#E2E8F0",
                  border:"1px solid rgba(255,255,255,.05)",
                  borderRadius:m.role==="user"?"16px 16px 4px 16px":"16px 16px 16px 4px",
                  boxShadow:"0 4px 12px rgba(0,0,0,.2)"}}>{m.content}</div>
              </div>
            ))}
            <InsightCardEmbed/>
          </div>
          <div style={{padding:12,borderTop:"1px solid rgba(255,255,255,.05)"}}>
            <div style={{display:"flex",gap:8,alignItems:"flex-end"}}>
              <textarea value={input} onChange={e=>setInput(e.target.value)} rows={2} placeholder="AI에게 데이터 분석 요청…"
                style={{flex:1,background:"rgba(11,14,46,.6)",color:"#E2E8F0",resize:"none",
                  border:"1px solid rgba(255,255,255,.05)",borderRadius:16,padding:"10px 14px",
                  font:"400 13px Pretendard,'Apple SD Gothic Neo',sans-serif",outline:"none"}}/>
              <div style={{marginBottom:-4}}><IconBtn icon={I.send} title="전송"
                onClick={()=>{ if(input.trim()){ setMessages([...messages,{role:"user",content:input}]); setInput("");} }}/></div>
            </div>
            <p style={{margin:"6px 0 0 4px",font:"400 10px Pretendard,'Apple SD Gothic Neo',sans-serif",color:"#4B5563"}}>Enter 전송 · Shift+Enter 줄바꿈</p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function InsightCardEmbed() {
  return (
    <div style={{background:"rgba(23,27,94,.4)",backdropFilter:"blur(8px)",borderRadius:16,padding:14,
      border:"1px solid rgba(255,255,255,.05)",boxShadow:"0 10px 40px rgba(0,0,0,.4)"}}>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:10}}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <div style={{width:22,height:22,borderRadius:8,background:"rgba(240,151,8,.2)",display:"flex",alignItems:"center",justifyContent:"center",color:"#F09708"}}>{I.zap}</div>
          <Eyebrow tone="accent">Target Detected</Eyebrow>
        </div>
        <span style={{font:"500 9px JetBrains Mono,monospace",color:"#9CA3AF",background:"rgba(255,255,255,.04)",
          border:"1px solid rgba(255,255,255,.08)",padding:"3px 8px",borderRadius:999}}>ID: X7K2Q9</span>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:8}}>
        <div style={{background:"rgba(11,14,46,.6)",border:"1px solid rgba(255,255,255,.05)",borderRadius:10,padding:"8px 10px"}}>
          <div style={{font:"700 9px Pretendard,'Apple SD Gothic Neo',sans-serif",textTransform:"uppercase",color:"#6B7280",marginBottom:4}}>Analysis Type</div>
          <div style={{font:"500 12px JetBrains Mono,monospace",color:"#fff"}}>force</div>
        </div>
        <div style={{background:"rgba(11,14,46,.6)",border:"1px solid rgba(255,255,255,.05)",borderRadius:10,padding:"8px 10px"}}>
          <div style={{font:"700 9px Pretendard,'Apple SD Gothic Neo',sans-serif",textTransform:"uppercase",color:"#6B7280",marginBottom:4}}>Normalization</div>
          <div style={{display:"flex",alignItems:"center",gap:6,color:"#00FFB2",font:"700 12px Pretendard,'Apple SD Gothic Neo',sans-serif"}}>
            <span style={{width:6,height:6,borderRadius:"50%",background:"#00FFB2",boxShadow:"0 0 5px #00FFB2"}}/>ACTIVE</div>
        </div>
      </div>
      <div style={{background:"rgba(11,14,46,.6)",border:"1px solid rgba(255,255,255,.05)",borderRadius:10,padding:"8px 10px"}}>
        <div style={{font:"700 9px Pretendard,'Apple SD Gothic Neo',sans-serif",textTransform:"uppercase",color:"#6B7280",marginBottom:6}}>Selected Columns</div>
        <div style={{display:"flex",flexWrap:"wrap",gap:6}}>
          <Chip>L_ActForce_N</Chip><Chip>R_ActForce_N</Chip><Chip>L_DesForce_N</Chip><Chip>R_DesForce_N</Chip>
        </div>
      </div>
    </div>
  );
}

// ==== Redesign target: Paper Studio card grid ====
function PaperStudio() {
  const [mode, setMode] = React.useState("quick");
  const [request, setRequest] = React.useState("");
  const [cards, setCards] = React.useState([
    { id: 1, title: "Force · L/R comparison", type: "force", state: "ready" },
    { id: 2, title: "IMU Pitch timeline", type: "imu", state: "ready" },
  ]);
  const [nextId, setNextId] = React.useState(3);

  const submit = () => {
    if (!request.trim()) return;
    const id = nextId;
    setCards([{ id, title: request, type: "force", state: "loading" }, ...cards]);
    setNextId(nextId+1);
    setRequest("");
    setTimeout(()=>{
      setCards(c=>c.map(x=>x.id===id?{...x,state:"ready"}:x));
    }, 1400);
  };

  return (
    <div style={{display:"flex",flexDirection:"column",height:"100vh",background:"#0B0E2E",color:"#E2E8F0",font:"400 13px Pretendard,'Apple SD Gothic Neo',sans-serif"}}>
      <TopNav mode={mode} setMode={setMode}/>

      {/* Upload strip + composer */}
      <div style={{padding:"16px 24px",display:"grid",gridTemplateColumns:"280px 1fr 220px",gap:16,alignItems:"center",
        background:"rgba(11,14,46,.5)",borderBottom:"1px solid rgba(255,255,255,.05)"}}>
        <div style={{display:"flex",alignItems:"center",gap:10,padding:"10px 14px",background:"rgba(23,27,94,.3)",
          border:"1px dashed rgba(240,151,8,.25)",borderRadius:12,cursor:"pointer"}}>
          <span style={{color:"#F09708"}}>{I.upload}</span>
          <div style={{display:"flex",flexDirection:"column",lineHeight:1.2}}>
            <span style={{fontSize:12,color:"#E2E8F0",fontWeight:600}}>Drop CSV or browse</span>
            <span style={{font:"500 10px JetBrains Mono,monospace",color:"#6B7280"}}>trial_2_imu.csv · +2 loaded</span>
          </div>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:8,background:"rgba(11,14,46,.6)",
          borderRadius:14,padding:"4px 4px 4px 16px",border:"1px solid rgba(255,255,255,.05)"}}>
          <span style={{color:"#F09708",fontWeight:700}}>&gt;</span>
          <input value={request} onChange={e=>setRequest(e.target.value)} onKeyDown={e=>e.key==="Enter"&&submit()}
            placeholder="예: 왼쪽 Force만 다시, 범례 빼고"
            style={{flex:1,background:"transparent",border:0,color:"#fff",font:"400 13px Pretendard,'Apple SD Gothic Neo',sans-serif",outline:"none"}}/>
          <PrimaryBtn icon={I.zap} onClick={submit}>Plot</PrimaryBtn>
        </div>
        <div style={{display:"flex",justifyContent:"flex-end",gap:8}}>
          <GhostBtn icon={I.dl}>Export all</GhostBtn>
        </div>
      </div>

      {/* Card grid */}
      <div style={{flex:1,overflow:"auto",padding:24,display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(320px,1fr))",gap:16,alignContent:"start"}}>
        {cards.map(c=><GraphCard key={c.id} card={c} onRemove={()=>setCards(cards.filter(x=>x.id!==c.id))}/>)}
      </div>
    </div>
  );
}

function GraphCard({ card, onRemove }) {
  const loading = card.state === "loading";
  return (
    <div style={{background:"rgba(23,27,94,.3)",border:"1px solid rgba(255,255,255,.06)",borderRadius:16,padding:14,
      display:"flex",flexDirection:"column",gap:10,minHeight:220,backdropFilter:"blur(8px)"}}>
      <div style={{display:"flex",alignItems:"center",gap:8}}>
        <Eyebrow tone={loading?"gray":"accent"}>{loading?"Loading…":card.type}</Eyebrow>
        <span style={{marginLeft:"auto",fontSize:13,color:"#fff",fontWeight:700,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:"60%"}}>{card.title}</span>
        <button onClick={onRemove} aria-label="remove" style={{background:"transparent",border:0,color:"#6B7280",cursor:"pointer",padding:4,display:"inline-flex"}}>{I.x}</button>
      </div>
      <div style={{flex:1,background:"rgba(11,14,46,.6)",borderRadius:10,minHeight:120,position:"relative",overflow:"hidden",
        ...(loading?{background:"linear-gradient(90deg,rgba(255,255,255,.02),rgba(240,151,8,.08),rgba(255,255,255,.02))",backgroundSize:"200% 100%",animation:"hwShimmer 1.8s infinite"}:{})}}>
        {!loading && (
          <svg viewBox="0 0 300 120" preserveAspectRatio="none" style={{width:"100%",height:"100%"}}>
            <polyline fill="none" stroke="#F09708" strokeWidth="1.5" points="0,90 30,85 60,60 90,30 120,50 150,40 180,25 210,40 240,20 270,55 300,75"/>
            <polyline fill="none" stroke="#00FFB2" strokeWidth="1.5" opacity=".85" points="0,80 30,72 60,62 90,45 120,55 150,35 180,32 210,42 240,30 270,52 300,70"/>
          </svg>
        )}
      </div>
      {!loading && (
        <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
          <Chip>peak L: 42.7 N</Chip>
          <Chip>peak R: 39.1 N</Chip>
          <Chip tone="mint">SI 8.4%</Chip>
          <div style={{marginLeft:"auto",display:"flex",gap:6}}>
            <GhostBtn icon={I.copy}>Dup</GhostBtn>
            <GhostBtn icon={I.dl}>SVG</GhostBtn>
          </div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { LegacyShell, PaperStudio, GraphCard, InsightCardEmbed });
