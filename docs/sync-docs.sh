#!/bin/bash
# H-Walker Graph App docs sync script
# 3개 위치 간 문서 동기화: project / vault / knowledge
# Usage: ./sync-docs.sh [--to-vault | --from-vault | --status]

set -e

PROJECT_DOCS="/Users/chobyeongjun/h-walker-ws/tools/graph_app/docs"
VAULT_DIR="/Users/chobyeongjun/0xhenry.dev/vault/Research/10_Wiki"
KNOWLEDGE_DIR="/Users/chobyeongjun/.hw_graph/knowledge"

# 파일 매핑: [project_filename, vault_filename]
declare -a FILES=(
  "HANDOVER-2026-04-17.md|H-Walker Graph App LLM Plotting 검증 수정 인수인계.md"
  "USAGE-QUICK-REFERENCE.md|H-Walker Graph App 사용 가이드.md"
  "IMPROVEMENTS-2026-04-17.md|H-Walker LLM 품질 개선 Phase 1.md"
)

KNOWLEDGE_FILE="h-walker-domain.md"
KNOWLEDGE_VAULT="h-walker-graph-app-knowledge.md"

case "${1:-}" in
  --to-vault)
    echo "📤 Project → Vault"
    for pair in "${FILES[@]}"; do
      src="${pair%|*}"
      dst="${pair#*|}"
      cp "$PROJECT_DOCS/$src" "$VAULT_DIR/$dst"
      echo "  ✓ $src → $dst"
    done
    cp "$KNOWLEDGE_DIR/$KNOWLEDGE_FILE" "$VAULT_DIR/$KNOWLEDGE_VAULT"
    echo "  ✓ knowledge 동기화"
    ;;

  --from-vault)
    echo "📥 Vault → Project"
    for pair in "${FILES[@]}"; do
      src="${pair%|*}"
      dst="${pair#*|}"
      cp "$VAULT_DIR/$dst" "$PROJECT_DOCS/$src"
      echo "  ✓ $dst → $src"
    done
    cp "$VAULT_DIR/$KNOWLEDGE_VAULT" "$KNOWLEDGE_DIR/$KNOWLEDGE_FILE"
    echo "  ✓ knowledge 동기화 (LLM 재시작 불필요)"
    ;;

  --status|"")
    echo "📊 문서 상태 비교"
    for pair in "${FILES[@]}"; do
      src="${pair%|*}"
      dst="${pair#*|}"
      p="$PROJECT_DOCS/$src"
      v="$VAULT_DIR/$dst"
      if diff -q "$p" "$v" > /dev/null 2>&1; then
        echo "  ✓ $src : 동기화됨"
      else
        echo "  ✗ $src : 차이 있음"
        echo "      project: $(stat -f '%Sm' "$p")"
        echo "      vault  : $(stat -f '%Sm' "$v")"
      fi
    done
    # Knowledge
    if diff -q "$KNOWLEDGE_DIR/$KNOWLEDGE_FILE" "$VAULT_DIR/$KNOWLEDGE_VAULT" > /dev/null 2>&1; then
      echo "  ✓ knowledge : 동기화됨"
    else
      echo "  ✗ knowledge : 차이 있음"
    fi
    ;;

  *)
    echo "Usage: $0 [--to-vault | --from-vault | --status]"
    echo "  --to-vault    : project/knowledge → vault 복사"
    echo "  --from-vault  : vault → project/knowledge 복사"
    echo "  --status      : 3 위치 간 차이 확인"
    exit 1
    ;;
esac

echo "완료."
