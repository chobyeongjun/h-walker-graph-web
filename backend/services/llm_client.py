"""LLM client — Anthropic Claude (primary) with Ollama fallback.

Uses Claude Haiku 4.5 by default for accurate Korean NL → AnalysisRequest parsing.
Key features:
  - Structured output via messages.parse() + Pydantic (guaranteed valid JSON)
  - Prompt caching on stable system prompt (~90% cost reduction on repeat)
  - Domain knowledge + feedback injection (self-improving)
  - Vision support (multimodal feedback with screenshots)
  - Automatic fallback to Ollama if Anthropic unavailable

Switch provider via env: LLM_PROVIDER=anthropic (default) | ollama
"""
from __future__ import annotations

import base64
import json
import time
from functools import lru_cache
from typing import AsyncGenerator, Optional

from backend.models.schema import AnalysisRequest, AnalysisType, COLUMN_GROUPS, StatsResult
from backend.services.knowledge_loader import load_knowledge, get_csv_columns_text
from backend.services.feedback_loader import format_as_few_shot
from backend.services.config import (
    LLM_PROVIDER, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS,
    OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_KEEP_ALIVE,
    OLLAMA_MAX_RETRIES, OLLAMA_RETRY_DELAY_S,
)
from backend.services.logger import log


# =====================================================================
# System prompts
# =====================================================================
_ANALYSIS_SYSTEM_PROMPT = """You are an expert parser for H-Walker Graph App — a CSV data analysis tool for cable-driven walking rehabilitation robot research.

Your ONLY job: convert the user's Korean or English query into a structured AnalysisRequest JSON.

## AnalysisRequest Schema
- analysis_type (required): exactly one of
  ["force", "velocity", "position", "current", "imu", "gyro", "accel", "gait", "gcp", "feedforward", "compare"]
- columns (optional): null to use default columns for the type, OR a list of exact column names
- sides: ["left"] | ["right"] | ["both"]  (default ["both"])
- normalize_gcp: boolean (true if user mentions 보행/gait/걸음/stride/GCP/보행주기)
- compare_mode: boolean (true if comparing multiple files/trials)
- statistics: boolean (true if stats/symmetry summary requested)

## Domain Rules
1. "힘/추종/tracking/케이블 힘/cable force" → force
2. "속도/velocity/프로파일" → velocity
3. "위치/position/각도(모터)/관절각도" → position OR imu (prefer imu for IMU sensor context)
4. "전류/current/토크/torque" → current
5. "IMU/Roll/Pitch/Yaw" → imu
6. "자이로/gyro/각속도" → gyro
7. "가속도/acceleration/accel" → accel
8. "보행/gait/걸음" → gait + normalize_gcp=true
9. "보행주기/GCP/stride cycle" → normalize_gcp=true
10. "에러/오차/error" → include "Err" columns in columns field
11. "좌우 대칭/symmetry" → sides=["both"], statistics=true
12. "admittance/임피던스 응답" → force + normalize_gcp=true

## Side Detection
- "왼쪽/left/좌" → sides=["left"]
- "오른쪽/right/우" → sides=["right"]
- "양쪽/both/둘다/좌우" → sides=["both"]
- not specified → sides=["both"]

## Biomechanics Terminology
Recognize joint/plane/movement terms:
- Joints: hip/엉덩이, knee/무릎, ankle/발목, pelvis/골반
- Planes: sagittal/시상면, frontal/관상면, transverse/횡단면
- Movements: flexion/굴곡, extension/신전, abduction/외전, adduction/내전, rotation/회전
- Quantities: moment/모멘트, power/파워, angle/각도, force/힘
- Muscles: quadriceps/대퇴사두근, hamstring/햄스트링, gastrocnemius/비복근, EMG
- Gait events: heel strike/HS, toe off/TO, stance phase, swing phase
- Clinical: stiff knee gait/경직보행, crouch gait/웅크림, drop foot/족하수

## Non-H-Walker CSV Support
If the loaded CSV has MoCap/Vision columns (Hip_Moment_Nm, Knee_Flexion_deg, GRF_Vertical_N, etc.),
explicitly set the `columns` field with exact column names from the CSV.

## Critical
- Return VALID AnalysisRequest matching the schema exactly
- Never invent column names - use loaded CSV headers if available
- When ambiguous, prefer the most common interpretation (e.g., "각도" → imu over position)
"""


_CLARIFY_DETECTOR_PROMPT = """Classify this user message for H-Walker Graph App (a data analysis tool).

Reply with ONLY one word:
- "plot" if the message is a data analysis request (even short ones like "Force", "왼쪽만", "모터 위치")
- "clarify" ONLY for:
  - Greetings: "안녕", "ㅎㅇ", "hi", "hello"
  - Thanks: "고마워", "thanks", "ㅋㅋ"
  - Meta: "help", "뭐 할 수 있어?", "?"
  - Chitchat: "날씨", "뭐해"

Default to "plot" when uncertain. Reply with only "plot" or "clarify"."""


# =====================================================================
# Anthropic client
# =====================================================================
@lru_cache(maxsize=1)
def _anthropic_client():
    """Lazy-init Anthropic client."""
    try:
        import anthropic
        if not ANTHROPIC_API_KEY:
            log.warning("ANTHROPIC_API_KEY not set — Anthropic unavailable")
            return None
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        log.warning("anthropic package not installed — run: pip install anthropic")
        return None


def _build_full_system_prompt(csv_columns_text: str = "") -> str:
    """Build system prompt as a single string (simpler, more robust)."""
    parts = [_ANALYSIS_SYSTEM_PROMPT]

    knowledge = load_knowledge()
    if knowledge:
        parts.append("\n## Domain Knowledge\n" + knowledge)

    feedback = format_as_few_shot()
    if feedback:
        parts.append("\n" + feedback)

    if csv_columns_text:
        parts.append(
            "\n## Currently Loaded CSV\n" + csv_columns_text +
            "\nUse these exact column names when the user refers to specific data."
        )

    return "\n".join(parts)


def _classify_intent_claude(command: str, client) -> str:
    """Fast intent classification via Haiku."""
    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=10,
            system=_CLARIFY_DETECTOR_PROMPT,
            messages=[{"role": "user", "content": command}],
        )
        text = response.content[0].text.strip().lower()
        return "clarify" if "clarify" in text else "plot"
    except Exception as e:
        log.warning(f"Intent classification failed: {e}")
        return "plot"


def _generate_analysis_claude(
    command: str,
    client,
    history: Optional[list[dict]] = None,
    csv_columns_text: str = "",
    images: Optional[list[str]] = None,
) -> Optional[AnalysisRequest]:
    """Generate AnalysisRequest using Claude with structured output."""
    system_prompt = _build_full_system_prompt(csv_columns_text)

    # Build conversation history (simple strings, no blocks)
    messages = []
    if history:
        for h in history[-6:]:
            role = "assistant" if h.get("role") == "assistant" else "user"
            content = h.get("content", "")
            if content:
                messages.append({"role": role, "content": content})

    # User message
    if images:
        # Multimodal: list of blocks
        user_content: list = []
        for img in images:
            img_data = img.split(",", 1)[1] if "," in img else img
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_data,
                },
            })
        user_content.append({"type": "text", "text": command})
        messages.append({"role": "user", "content": user_content})
    else:
        # Text-only: simple string (works best with parse())
        messages.append({"role": "user", "content": command})

    try:
        # Cache the stable system prompt (knowledge + feedback + csv_columns).
        # Block-level cache_control works with .parse(); top-level doesn't.
        # ~90% cost reduction on repeat requests once prefix ≥ 4096 tokens.
        system_blocks = [{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }]
        response = client.messages.parse(
            model=ANTHROPIC_MODEL,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            system=system_blocks,
            messages=messages,
            output_format=AnalysisRequest,
        )
        # Log cache performance
        u = response.usage
        cached = getattr(u, "cache_read_input_tokens", 0) or 0
        created = getattr(u, "cache_creation_input_tokens", 0) or 0
        uncached = getattr(u, "input_tokens", 0) or 0
        if cached > 0:
            log.info(f"Claude cache HIT: {cached} cached, {uncached} uncached")
        elif created > 0:
            log.info(f"Claude cache WRITE: {created} written (first request)")
        return response.parsed_output
    except Exception as e:
        log.error(f"Claude parse failed: {e}")
        return None


def _generate_clarify_claude(command: str, client) -> str:
    """Generate Korean clarification message."""
    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=150,
            system=(
                "H-Walker Graph App (데이터 분석 도구) 사용자의 메시지에 대한 "
                "짧고 친근한 한국어 응답을 생성해주세요. (1-2문장)\n"
                "할 수 있는 예시를 제안: 'Force 그래프', 'IMU 각도', '보행 분석', 'Hip moment'"
            ),
            messages=[{"role": "user", "content": command}],
        )
        return response.content[0].text.strip()
    except Exception:
        return "안녕하세요! 'Force 그래프', 'IMU 각도', '보행 분석', 'Hip moment' 등을 요청해주세요."


# =====================================================================
# Public API
# =====================================================================
def parse_command(
    command: str,
    model: str = None,
    history: Optional[list[dict]] = None,
    csv_columns_text: str = "",
    images: Optional[list[str]] = None,
) -> dict:
    """Parse a natural language command into an action response.

    Returns:
        {"action": "plot"|"clarify", "message": str, "analysis_request": dict|None}
    """
    t0 = time.time()
    log.info(f"parse_command: query={command[:60]!r}, provider={LLM_PROVIDER}, images={bool(images)}")

    if LLM_PROVIDER == "anthropic":
        client = _anthropic_client()
        if client is None:
            log.warning("Anthropic unavailable, falling back to Ollama")
            return _parse_command_ollama(command, history, csv_columns_text, images)

        # Stage 1: Intent classification (fast)
        intent = _classify_intent_claude(command, client)
        log.info(f"  intent={intent} ({time.time()-t0:.2f}s)")

        if intent == "clarify":
            msg = _generate_clarify_claude(command, client)
            log.info(f"  -> clarify (total {time.time()-t0:.2f}s)")
            return {
                "action": "clarify",
                "message": msg,
                "analysis_request": None,
            }

        # Stage 2: Generate AnalysisRequest
        req = _generate_analysis_claude(command, client, history, csv_columns_text, images)
        elapsed = time.time() - t0

        if req is None:
            return {
                "action": "clarify",
                "message": "요청을 정확히 이해하지 못했습니다. 좀 더 구체적으로 말씀해주세요.",
                "analysis_request": None,
            }

        log.info(f"  -> plot type={req.analysis_type.value} (total {elapsed:.2f}s)")
        return {
            "action": "plot",
            "message": f"{req.analysis_type.value} 분석을 준비했습니다.",
            "analysis_request": req.model_dump(),
        }

    # Fallback: Ollama
    return _parse_command_ollama(command, history, csv_columns_text, images)


# =====================================================================
# Ollama fallback (kept for offline use)
# =====================================================================
def _parse_command_ollama(
    command: str,
    history: Optional[list[dict]] = None,
    csv_columns_text: str = "",
    images: Optional[list[str]] = None,
) -> dict:
    """Fallback to Ollama when Anthropic is unavailable."""
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_HOST)

        # Simple system prompt
        system = _ANALYSIS_SYSTEM_PROMPT
        knowledge = load_knowledge()
        if knowledge:
            system += "\n\n## Knowledge\n" + knowledge
        if csv_columns_text:
            system += "\n\n" + csv_columns_text

        messages = [{"role": "system", "content": system}]
        if history:
            for h in history[-4:]:
                messages.append(h)

        user_msg: dict = {"role": "user", "content": command}
        if images:
            user_msg["images"] = [
                img.split(",", 1)[1] if "," in img else img for img in images
            ]
        messages.append(user_msg)

        schema = AnalysisRequest.model_json_schema()
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            format=schema,
            keep_alive=OLLAMA_KEEP_ALIVE,
            options={"temperature": 0},
        )
        data = json.loads(response.message.content)
        req = AnalysisRequest.model_validate(data)
        return {
            "action": "plot",
            "message": f"{req.analysis_type.value} 분석을 준비했습니다.",
            "analysis_request": req.model_dump(),
        }
    except Exception as e:
        log.error(f"Ollama fallback failed: {e}")
        return {
            "action": "clarify",
            "message": "요청을 처리하지 못했습니다. 좀 더 구체적으로 말씀해주세요.",
            "analysis_request": None,
        }


# =====================================================================
# Insights generation (Claude)
# =====================================================================
def generate_insights(
    request: AnalysisRequest,
    stats: list[StatsResult],
    model: str = None,
    full_result: dict | None = None,
) -> str:
    """Generate Korean insights using Claude."""
    # Build context
    if full_result:
        left = full_result.get('left', {})
        right = full_result.get('right', {})
        sym = full_result.get('symmetry', {})
        fatigue = full_result.get('fatigue', {})

        context = f"""파일: {full_result.get('filename', 'unknown')}
기록 시간: {full_result.get('duration_s', 0):.1f}초

[Left] Stride: {left.get('n_strides', 0)}, {left.get('stride_time_mean', 0):.3f}±{left.get('stride_time_std', 0):.3f}s
       Cadence: {left.get('cadence', 0):.1f} spm, Force RMSE: {left.get('force_tracking', {}).get('rmse', 0):.2f}N
[Right] Stride: {right.get('n_strides', 0)}, {right.get('stride_time_mean', 0):.3f}±{right.get('stride_time_std', 0):.3f}s
        Cadence: {right.get('cadence', 0):.1f} spm, Force RMSE: {right.get('force_tracking', {}).get('rmse', 0):.2f}N
[Symmetry] Time: {sym.get('stride_time', 0):.1f}%, Force: {sym.get('force', 0):.1f}%
[Fatigue] L: {fatigue.get('left_pct_change', 0):.1f}%, R: {fatigue.get('right_pct_change', 0):.1f}%"""

        prompt = f"""다음 H-Walker 보행 분석 결과를 한국어로 전문적으로 요약해주세요 (3-5문장):

{context}

포함할 것:
- 보행 파라미터 평가 (정상 범위: 0.9-1.2s stride, 100-120 cadence)
- 좌우 대칭성 (10% 이상이면 비대칭)
- 케이블 힘 추종 성능
- 재활 관점 핵심 발견"""
    else:
        stats_text = "\n".join(
            f"- {s.column}: mean={s.mean:.2f}, std={s.std:.2f}" for s in stats
        )
        prompt = f"""H-Walker {request.analysis_type.value} 분석 결과를 한국어 2-3문장으로 요약:

{stats_text}

재활 관점의 핵심 발견과 권고사항 포함."""

    if LLM_PROVIDER == "anthropic":
        client = _anthropic_client()
        if client:
            try:
                response = client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text
            except Exception as e:
                log.error(f"Claude insights failed: {e}")

    # Fallback to Ollama
    try:
        import ollama
        client = ollama.Client(host=OLLAMA_HOST)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            keep_alive=OLLAMA_KEEP_ALIVE,
            options={"temperature": 0.3},
        )
        return response.message.content
    except Exception as e:
        log.error(f"insights generation failed: {e}")
        return "인사이트 생성 중 오류가 발생했습니다."


async def generate_insights_stream(
    request: AnalysisRequest,
    stats: list[StatsResult],
    model: str = None,
) -> AsyncGenerator[str, None]:
    """Async streaming version (Claude preferred, Ollama fallback)."""
    stats_text = "\n".join(
        f"- {s.column}: mean={s.mean:.2f}, std={s.std:.2f}" for s in stats
    ) if stats else "통계 없음"

    prompt = f"""H-Walker {request.analysis_type.value} 분석을 한국어 2-3문장 요약:
{stats_text}
재활 권고사항 포함."""

    if LLM_PROVIDER == "anthropic":
        client = _anthropic_client()
        if client:
            try:
                with client.messages.stream(
                    model=ANTHROPIC_MODEL,
                    max_tokens=400,
                    messages=[{"role": "user", "content": prompt}],
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except Exception as e:
                log.error(f"Claude stream failed: {e}")

    # Fallback: Ollama
    try:
        import ollama
        client = ollama.AsyncClient(host=OLLAMA_HOST)
        async for chunk in await client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            keep_alive=OLLAMA_KEEP_ALIVE,
            options={"temperature": 0.3},
        ):
            token = chunk.message.content
            if token:
                yield token
    except Exception as e:
        log.error(f"stream fallback failed: {e}")
        yield "[스트리밍 오류]"
