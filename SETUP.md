# Fresh Install Guide — H-Walker Graph Web

완전히 빈 계정 / 컴퓨터에서 처음부터 돌리는 법. Mac / Linux / WSL 기준.

---

## 1. Prerequisites (이거 셋만 있으면 됨)

| 도구 | 최소 버전 | 확인 명령 | 없으면 |
|---|---|---|---|
| Python 3 | 3.10+ | `python3 --version` | [python.org](https://www.python.org/downloads/) |
| Node.js | 20.x+ | `node --version` | [nodejs.org](https://nodejs.org) (LTS) |
| Git | any | `git --version` | `xcode-select --install` (Mac) |

Mac에서 Homebrew 쓰면 한 줄:
```bash
brew install python@3.13 node git
```

---

## 2. Anthropic API Key

[console.anthropic.com](https://console.anthropic.com) 에서 API 키 발급. Haiku 4.5 호출 1회에 보통 $0.0001~$0.001 정도.

```bash
# 지금 세션에만 (설치 테스트용)
export ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxx

# 영구적으로 (zsh 기준)
echo 'export ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxx' >> ~/.zshrc
source ~/.zshrc
```

---

## 3. Clone + Install (3 steps, 한 번만)

```bash
# 1) 클론
git clone https://github.com/chobyeongjun/h-walker-graph-web.git
cd h-walker-graph-web

# 2) 파이썬 의존성
pip3 install -r requirements.txt

# 3) 프론트엔드 의존성 + 빌드 (한 번만)
cd frontend
npm install
npm run build
cd ..
```

> **pip / pip3:** Mac/Linux 는 `pip3` 권장 (Python 2와 혼동 방지). `pip: command not found` 나면 `python3 -m pip install -r requirements.txt`.
>
> **npm install 처음 1회만** — node_modules 생성되면 이후엔 `npm run build`만 다시 돌리면 됨.

---

## 4. Run

```bash
python3 run.py
# → 브라우저가 자동으로 http://localhost:8000 을 엶
```

또는 포트 바꾸기:
```bash
python3 run.py --port 8080
python3 run.py --port 8000 --no-browser  # 브라우저 자동실행 끄기
```

확인:
```bash
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/api/claude/health
# {"provider":"anthropic","model":"claude-haiku-4-5","key_present":true}
#                                                    ^^^^^^^^^^^^^^^^^^
# false 면 ANTHROPIC_API_KEY 를 export 안 한 상태. 2번 다시.
```

---

## 5. 개발 모드 (핫리로드, 선택사항)

프론트엔드 수정하면서 바로 반영되게 하고 싶으면:
```bash
# 터미널 A — 백엔드
cd h-walker-graph-web
python3 run.py

# 터미널 B — Vite dev server (핫리로드)
cd h-walker-graph-web/frontend
npm run dev
# → http://localhost:5173  (이쪽으로 접속. /api/* 는 8000으로 프록시됨)
```

---

## 6. 데스크톱 앱 (Phase 2D) — 아이콘 더블클릭 실행

pywebview 기반 네이티브 윈도우에서 바로 열림 (브라우저 열 필요 없음):

```bash
# 개발 실행
pip3 install pywebview          # requirements.txt에 이미 포함
python3 desktop.py              # 네이티브 창 pop
python3 desktop.py --headless   # pywebview 스킵, 기존 브라우저 모드로
```

아이콘 재생성 (로고 SVG 변경 시):
```bash
pip3 install cairosvg           # requirements.txt에 이미 포함
python3 tools/build_icons.py
# → AppIcon.icns (mac) + AppIcon.ico (win) + icons/*.png 전부 재생성
```

### 6-1. macOS .app 번들

```bash
pip3 install py2app
cd frontend && npm run build && cd ..
python3 tools/build_icons.py
python3 packaging/setup_py2app.py py2app
# → dist/H-Walker CORE.app
open "dist/H-Walker CORE.app"   # 더블클릭과 동일
```

서명 없는 앱 처음 열 때 Mac 보안 경고: **우클릭 → Open → 확인**. 서명/공증은
별도(`codesign` + `notarytool`).

### 6-2. Windows / Linux 번들

```bash
pip install pyinstaller
cd frontend && npm run build && cd ..
python3 tools/build_icons.py
pyinstaller packaging/hwalker.spec --noconfirm
# → dist/H-Walker CORE/H-Walker CORE(.exe)
```

### 6-3. 빠른 시작용 alias (번들 없이)

```bash
echo 'alias hwalker="cd ~/h-walker-graph-web && python3 desktop.py"' >> ~/.zshrc
source ~/.zshrc
# 이제 어디서든 hwalker 치면 네이티브 창 pop
```

---

## 7. 자주 만나는 문제

### ❌ `ModuleNotFoundError: No module named 'tools'`
- 원인: 리포 루트가 아닌 하위 폴더에서 실행
- 해결: `cd ~/h-walker-graph-web` 후 `python3 run.py`

### ❌ `ANTHROPIC_API_KEY is not set`
- 원인: env 안 export 됨
- 해결: 같은 터미널에서 `export ANTHROPIC_API_KEY=sk-ant-...` 후 재실행

### ❌ `EADDRINUSE :::8000`
- 원인: 8000 이미 사용 중
- 해결: `python3 run.py --port 8080` 또는 `lsof -ti:8000 | xargs kill -9`

### ❌ `npm install` 실패 / EBADENGINE
- 원인: Node 버전 너무 낮음
- 해결: Node 20+ 설치 (`brew install node@20` 또는 [nvm](https://github.com/nvm-sh/nvm))

### ❌ 프론트엔드가 dist 없다고 경고
- 원인: `npm run build` 안 함
- 해결: `cd frontend && npm install && npm run build && cd ..`

### ❌ Claude 응답이 `Claude endpoint error` 로 나옴
- `curl http://localhost:8000/api/claude/health` 로 `key_present` 확인
- `pip3 install --upgrade anthropic` 으로 SDK 업그레이드
- 워크스페이스에 크레딧 있는지 console.anthropic.com 에서 확인

---

## 8. 삭제할 때

```bash
# 로컬 데이터 (업로드된 CSV, 피드백, 로그)
rm -rf ~/.hw_graph

# 코드
rm -rf ~/h-walker-graph-web
```

**끝.** 다른 계정에서도 위 3–4 단계만 따라하면 똑같이 돌아감. 연구실에서 공용으로 쓰려면 pyenv/nvm 으로 버전 고정하면 더 깔끔.
