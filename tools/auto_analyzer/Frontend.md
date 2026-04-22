전체 구조
tools/graph_app/frontend/src/
├── App.tsx                    ← 전체 레이아웃 (3패널 배치)
├── index.css                  ← Tailwind 기본 설정
├── store.ts                   ← 상태관리 (건드리지 말 것)
├── api.ts                     ← API 통신 (건드리지 말 것)
├── types.ts                   ← 타입 정의 (건드리지 말 것)
└── components/
    ├── LeftPanel.tsx           ← 왼쪽 파일 브라우저 + 분석 버튼
    ├── DrivePanel.tsx          ← Google Drive 트리 + 로컬 업로드
    ├── GraphCanvas.tsx         ← 중앙 그래프 영역
    ├── PublicationBar.tsx      ⛔ 논문용 — 수정 금지
    ├── AIPanel.tsx             ← 오른쪽 AI 채팅
    └── InsightCard.tsx         ← 분석 요청 카드
수정 가능 / 불가 구분
파일	수정	설명
App.tsx	O	전체 레이아웃, 네비게이션 바
LeftPanel.tsx	O	왼쪽 사이드바
DrivePanel.tsx	O	파일 트리 UI
GraphCanvas.tsx	부분	빈 상태/로딩 스피너만 수정. Plotly/SVG 렌더링 로직 유지
AIPanel.tsx	O	채팅 UI, 메시지 버블
InsightCard.tsx	O	분석 카드 디자인
PublicationBar.tsx	X	논문 저널 선택 — 수정 금지
store.ts	X	상태 로직 — 수정 금지
api.ts	X	API 통신 — 수정 금지
types.ts	X	타입 — 수정 금지
index.css	O	글로벌 스타일 추가 가능
파일별 디자인 변경 가이드
1. App.tsx — 전체 레이아웃 + 네비게이션
현재 구조:

<div className="flex flex-col h-screen bg-gray-950 text-white">
  {/* 상단 네비게이션 */}
  <nav className="flex items-center gap-4 px-4 py-2 bg-gray-900 border-b border-gray-700 shrink-0">
    <span className="font-bold text-sm">H-Walker Graph</span>
    {/* Quick / Publication 모드 버튼 */}
    <button className={mode === 'quick' ? 'bg-blue-600 ...' : 'bg-gray-700 ...'}>
      Quick
    </button>
    <button className={mode === 'publication' ? 'bg-green-700 ...' : 'bg-gray-700 ...'}>
      Publication
    </button>
  </nav>

  {/* 3패널 본문 */}
  <div className="flex flex-1 overflow-hidden">
    <LeftPanel />      {/* 왼쪽: w-64 고정 */}
    <GraphCanvas />    {/* 중앙: flex-1 (나머지 공간) */}
    <AIPanel />        {/* 오른쪽: w-80 고정 */}
  </div>
</div>
바꿀 수 있는 것:

배경색: bg-gray-950 → 원하는 색
네비 바: 높이, 색상, 로고, 폰트
모드 버튼: 색상, 크기, 아이콘 추가
패널 너비: w-64(왼쪽), w-80(오른쪽) 변경 가능
유지할 것:

mode 상태 연결: onClick={() => setMode('quick')} 로직
3패널 flex 구조 자체 (LeftPanel / GraphCanvas / AIPanel 순서)
2. LeftPanel.tsx — 왼쪽 사이드바
현재 구조:

<div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col shrink-0">
  {/* DrivePanel — 파일 브라우저 */}
  <DrivePanel onFileSelected={handleFileSelected} />

  {/* 파일 카운트 */}
  {csvPaths.length > 0 && (
    <div className="px-3 py-1 text-xs text-blue-400 ...">
      {csvPaths.length}개 파일 로드됨
    </div>
  )}

  {/* 분석 버튼 */}
  <button className="mx-3 mb-3 bg-blue-600 hover:bg-blue-700 ...">
    {isLoading ? '분석 중...' : '분석'}
  </button>
</div>
바꿀 수 있는 것:

전체 너비 (w-64), 배경색, 보더 스타일
분석 버튼 색상/크기/모양
파일 카운트 표시 스타일
유지할 것:

<DrivePanel onFileSelected={handleFileSelected} /> 그대로
분석 버튼의 onClick={handleAnalyze}, disabled 조건
3. DrivePanel.tsx — 파일 브라우저
현재 구조:

{/* 탭 바: Google Drive / Local File */}
<div className="flex border-b">
  <button className={activeTab === 'drive' ? 'border-b-2 border-blue-500 ...' : '...'}>
    Google Drive
  </button>
  <button className={activeTab === 'local' ? '...' : '...'}>
    Local File
  </button>
</div>

{/* Drive 탭 내용 */}
{authStatus === 'unauthenticated' && (
  <a href={authUrl} className="bg-blue-500 text-white px-4 py-2 rounded ...">
    Connect Google Drive
  </a>
)}

{/* 검색바 */}
<input placeholder="날짜 또는 파일명 검색" className="... text-xs border rounded px-2 py-1" />

{/* 폴더 트리: FolderNode 재귀 컴포넌트 */}
<FolderNode folder={rootFolder} ... />
  → 📁 폴더이름 (▶/▼ 토글)
  → 📄 파일이름 (클릭시 다운로드)

{/* 에러 메시지 */}
{error && <div className="text-xs text-red-500 bg-red-50 ...">{error}</div>}
바꿀 수 있는 것:

탭 디자인 (색상, 아이콘 추가)
폴더/파일 아이콘 (현재 📁📄 이모지 → SVG 아이콘 등)
검색바 스타일
인증 화면 디자인
에러 메시지 스타일
다운로드 중 표시 (현재 ⏳ 이모지)
유지할 것:

onFileSelected prop 호출
driveAuthStatus(), driveFiles(), driveDownload(), driveSearch() API 호출
uploadFiles() 로컬 업로드 로직
FolderNode의 loadChildren 재귀 로직
4. GraphCanvas.tsx — 중앙 그래프 영역
현재 구조:

<div className="flex-1 flex flex-col bg-gray-950 overflow-hidden">
  {/* Publication 모드일 때만 PublicationBar 표시 — 수정 금지 */}
  {mode === 'publication' && <PublicationBar />}

  <div className="flex-1 flex items-center justify-center overflow-auto p-4">
    {/* 로딩 스피너 */}
    {isLoading && (
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
    )}

    {/* Quick 모드: Plotly 차트 */}
    {!isLoading && mode === 'quick' && plotlyData && (
      <Plot data={plotlyData.data} layout={{...plotlyData.layout, paper_bgcolor: 'transparent', ...}} />
    )}

    {/* Publication 모드: SVG 이미지 */}
    {!isLoading && mode === 'publication' && svgContent && (
      <div className="max-w-full max-h-full overflow-auto bg-white rounded p-4"
           dangerouslySetInnerHTML={{ __html: svgContent }} />
    )}

    {/* 빈 상태 */}
    {!isLoading && !plotlyData && !svgContent && (
      <div className="text-gray-600 text-center">
        <p className="text-4xl mb-4">📊</p>
        <p>파일을 선택하고 AI에게 분석을 요청하세요</p>
      </div>
    )}
  </div>
</div>
바꿀 수 있는 것:

배경색 (bg-gray-950)
로딩 스피너 디자인 (색, 크기, 애니메이션)
빈 상태 화면 (이모지, 텍스트, 일러스트)
SVG 래퍼 스타일 (bg-white rounded p-4)
절대 수정 금지:

{mode === 'publication' && <PublicationBar />} — 이 줄 유지
<Plot data={...} layout={...} /> — Plotly 렌더링 로직
dangerouslySetInnerHTML={{ __html: svgContent }} — SVG 렌더링 로직
Plotly layout의 paper_bgcolor, plot_bgcolor 등 차트 내부 스타일
5. AIPanel.tsx — AI 채팅
현재 구조:

<div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col shrink-0">
  {/* 헤더 */}
  <div className="px-4 py-3 border-b border-gray-700">
    <h2 className="font-semibold text-sm">AI 분석</h2>
  </div>

  {/* 메시지 목록 */}
  <div className="flex-1 overflow-y-auto p-3 space-y-3">
    {messages.map((msg) => (
      <div className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
        <div className={msg.role === 'user'
          ? 'bg-blue-700 text-white max-w-[90%] rounded px-3 py-2 text-sm'
          : 'bg-gray-800 text-gray-200 max-w-[90%] rounded px-3 py-2 text-sm whitespace-pre-wrap'
        }>
          {msg.content}
        </div>
      </div>
    ))}
    {/* InsightCard — 수정 가능 */}
    {lastAnalysisRequest && <InsightCard request={lastAnalysisRequest} />}
  </div>

  {/* 입력창 */}
  <div className="p-3 border-t border-gray-700 flex gap-2">
    <textarea className="flex-1 bg-gray-800 text-white rounded px-3 py-2 text-sm resize-none ..." />
    <button className="bg-blue-600 hover:bg-blue-700 text-white rounded px-3 py-2 text-sm ...">
      전송
    </button>
  </div>
</div>
바꿀 수 있는 것:

패널 너비 (w-80)
헤더 디자인 (제목, 아이콘, 배경)
메시지 버블 색상/모양/폰트 (bg-blue-700 유저, bg-gray-800 AI)
입력창 디자인 (크기, placeholder, 테두리)
전송 버튼 디자인
유지할 것:

messages.map() 렌더링 로직
msg.role === 'user' 분기
WebSocket 연결 (createChatWebSocket())
textarea의 onKeyDown Enter 전송 로직
<InsightCard request={lastAnalysisRequest} /> 연결
6. InsightCard.tsx — 분석 요청 카드
현재 구조:

<div className="bg-gray-800 rounded p-3 text-xs space-y-1 border border-gray-600">
  <p className="text-blue-400 font-semibold text-sm mb-2">분석 요청 감지</p>
  <div className="flex gap-2">
    <span className="text-gray-400">유형:</span>
    <span className="text-white">{request.analysis_type}</span>
  </div>
  {/* columns, normalize_gcp, compare_mode 등 */}
</div>
바꿀 수 있는 것: 전체 디자인 자유롭게 변경 가능 (색상, 레이아웃, 아이콘)

유지할 것:

props request: AnalysisRequest 구조
request.analysis_type, request.columns, request.normalize_gcp, request.compare_mode 표시
기술 스택 참고
스타일링: Tailwind CSS 3 (클래스 기반, CSS 파일 별도 작성 안 해도 됨)
아이콘: 현재 이모지 사용 중 → lucide-react, heroicons 등 설치 가능
폰트: 기본 시스템 폰트 → Google Fonts 추가 가능 (index.html 수정)
다크 테마: 현재 다크 모드 고정 (bg-gray-950 베이스)
개발/확인 방법
cd tools/graph_app/frontend
npm run dev
# http://localhost:5173 에서 확인
Tailwind 클래스만 바꾸면 핫 리로드로 즉시 반영됩니다.