#!/bin/bash
cd "$(dirname "$0")"
# ANTHROPIC_API_KEY는 ~/.zshrc에 export 해두셨다면 자동 로드됨
source ~/.zshrc 2>/dev/null
python3 run.py
