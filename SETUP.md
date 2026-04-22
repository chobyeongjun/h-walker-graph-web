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

## 6. Mac .app 번들 (선택사항)

아이콘 더블클릭으로 실행하고 싶으면:
```bash
# 리포지토리에 이미 AppIcon.icns 포함. 필요시 재생성:
sips -s format png -Z 1024 frontend/public/brand/mark-dark.svg --out /tmp/icon.png
# 자세한 스크립트는 docs/MAKE_APP.md 참고 (있으면)
```
또는 그냥 `python3 run.py` 를 zshrc alias 로 등록:
```bash
echo 'alias hwgraph="cd ~/h-walker-graph-web && python3 run.py"' >> ~/.zshrc
source ~/.zshrc
# 이제 어디서든 hwgraph 치면 실행됨
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
