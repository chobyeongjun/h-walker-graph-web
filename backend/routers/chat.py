"""
Chat router for H-Walker Graph App.

POST /api/chat        — single-turn: text → AnalysisRequest or clarification
WS   /ws/chat         — streaming: text → AnalysisRequest + insight tokens
GET  /api/chat/models — list available Ollama models
"""
from __future__ import annotations

from collections import deque

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

# Ollama is an optional dependency (Anthropic is the default provider as
# of Phase 2B). Import lazily inside the one endpoint that needs it so
# environments without the ollama SDK can still run tests and serve the
# Claude-only surface.

from backend.models.schema import AnalysisRequest
from backend.models.chat_schema import ChatRequest, ChatResponse, ChatMessage
from backend.services.llm_client import parse_command, generate_insights_stream, generate_insights
from backend.services.analysis_engine import run_full_analysis, result_to_dict, full_analysis_to_stats
from backend.services.knowledge_loader import get_csv_columns_text
from backend.services.feedback_detector import detect_sentiment
from backend.services.feedback_loader import save_positive, save_correction
from backend.services.session_state import get_session

router = APIRouter(prefix="/api/chat", tags=["chat"])
ws_router = APIRouter(tags=["chat-ws"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    """Single-turn: parse NL command → AnalysisRequest or clarification.

    Also auto-detects implicit feedback ("이거 이상해" / "맞아") and saves.
    """
    session = get_session()

    # ---- Auto-detect implicit feedback about the LAST response ----
    sentiment = detect_sentiment(request.message)
    if sentiment and session.get_last():
        last = session.get_last()
        if last.get("request"):
            try:
                if sentiment == "positive":
                    save_positive(
                        query=last["query"],
                        response=last["request"],
                        note="auto-detected from chat",
                    )
                elif sentiment == "negative":
                    save_correction(
                        query=last["query"],
                        wrong_response=last["request"],
                        reason=request.message,
                    )
            except Exception:
                pass  # feedback save failure shouldn't break chat

    # ---- Build context (CSV columns + recent analysis) ----
    csv_context = get_csv_columns_text()
    context_summary = session.get_context_summary()
    combined_context = csv_context + context_summary

    history = [{"role": h.role, "content": h.content} for h in request.history]

    try:
        result = parse_command(
            request.message,
            history=history,
            csv_columns_text=combined_context,
            images=request.images or None,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    action = result.get("action", "plot")
    message = result.get("message", "")
    analysis_req = None
    insights = []

    if action == "plot" and result.get("analysis_request"):
        try:
            analysis_req = AnalysisRequest.model_validate(result["analysis_request"])
        except Exception:
            # If validation fails, fall back to clarify
            action = "clarify"
            message = message or "분석 요청을 처리하지 못했습니다. 좀 더 구체적으로 말씀해주세요."

    if action == "plot" and analysis_req and analysis_req.file_paths:
        try:
            for fp in analysis_req.file_paths:
                ar_result = run_full_analysis(fp)
                result_dict = result_to_dict(ar_result)
                stats = full_analysis_to_stats(ar_result)
                insight = generate_insights(
                    analysis_req, stats, full_result=result_dict,
                )
                insights.append(insight)
        except Exception:
            pass  # Insights are optional

    # Record in session for follow-up context
    if action == "plot" and analysis_req:
        session.record(
            query=request.message,
            request=analysis_req,
            csv_paths=analysis_req.file_paths or None,
        )
    else:
        session.record(query=request.message)

    return ChatResponse(
        message=message or f"분석 요청을 파싱했습니다: {analysis_req.analysis_type if analysis_req else 'N/A'}",
        action=action,
        analysis_request=analysis_req,
        insights=insights,
    )


@router.get("/models")
async def list_models() -> dict[str, list[str]]:
    """Return active LLM model name (Claude or Ollama)."""
    from backend.services.config import LLM_PROVIDER, ANTHROPIC_MODEL, OLLAMA_MODEL

    if LLM_PROVIDER == "anthropic":
        return {"models": [ANTHROPIC_MODEL]}

    try:
        import ollama
        result = ollama.list()
        models = [m.model for m in result.models]
        return {"models": models}
    except Exception:
        return {"models": [OLLAMA_MODEL]}  # fallback


@ws_router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """Streaming chat WebSocket.

    Client → Server: {"message": "...", "history": [...]}
    Server → Client:
        {"type": "analysis_request", "data": {...}}  — when action="plot"
        {"type": "clarify", "data": "..."}            — when action="clarify"
        {"type": "token", "data": "..."}
        {"type": "done"}
        {"type": "error", "data": "..."}
    """
    await websocket.accept()
    history: deque[ChatMessage] = deque(maxlen=20)

    try:
        while True:
            raw = await websocket.receive_json()
            user_msg = raw.get("message", "")
            for h in raw.get("history", []):
                history.append(ChatMessage(**h))
            history.append(ChatMessage(role="user", content=user_msg))

            # Get CSV column context
            csv_context = get_csv_columns_text()
            hist_dicts = [{"role": h.role, "content": h.content} for h in history]

            try:
                result = parse_command(
                    user_msg,
                    history=hist_dicts,
                    csv_columns_text=csv_context,
                )
            except Exception as e:
                await websocket.send_json({"type": "error", "data": str(e)})
                continue

            action = result.get("action", "plot")

            if action == "clarify":
                await websocket.send_json({
                    "type": "clarify",
                    "data": result.get("message", "좀 더 구체적으로 말씀해주세요."),
                })
                history.append(ChatMessage(
                    role="assistant",
                    content=result.get("message", ""),
                ))
                await websocket.send_json({"type": "done"})
                continue

            # action == "plot"
            analysis_req = None
            if result.get("analysis_request"):
                try:
                    analysis_req = AnalysisRequest.model_validate(result["analysis_request"])
                except Exception:
                    await websocket.send_json({
                        "type": "error",
                        "data": "분석 요청 형식 오류",
                    })
                    continue

            if analysis_req:
                await websocket.send_json({
                    "type": "analysis_request",
                    "data": analysis_req.model_dump(),
                })

            # Stream insights
            full_response = []
            async for token in generate_insights_stream(
                analysis_req or AnalysisRequest(analysis_type="force"),
                stats=[],
            ):
                await websocket.send_json({"type": "token", "data": token})
                full_response.append(token)

            await websocket.send_json({"type": "done"})
            history.append(ChatMessage(
                role="assistant",
                content="".join(full_response),
            ))

    except WebSocketDisconnect:
        pass
