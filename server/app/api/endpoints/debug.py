"""
Debug endpoint for comparing AI model responses on schedule planning.
Used to optimize prompts and identify model inconsistencies.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
import json
from datetime import datetime

from ...db.database import get_session
from ...models.user import User
from ...services.ai_service import ai_service
from .auth import get_current_user

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("/compare-models")
def compare_ai_models(
    request: dict,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Call all available AI models with the same input and compare responses.

    Request body:
    {
        "user_message": "明天下午三點跟小明在信義區吃飯",
        "conversation_history": [...],
        "current_data": {...},
        "schedule_list": [...],
        "memory_snippets": [...],
        "contact_hints": [...]
    }

    Returns comparison of all models' outputs with quality assessment.
    """
    user_message = request.get("user_message", "").strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="user_message is required")

    conversation_history = request.get("conversation_history", [])
    current_data = request.get("current_data", {})
    schedule_list = request.get("schedule_list", [])
    memory_snippets = request.get("memory_snippets", [])
    contact_hints = request.get("contact_hints", [])

    results = {}

    # Call each provider separately and compare
    for idx, (_cli, _model, _label) in enumerate(ai_service._providers):
        try:
            result = ai_service.process_conversation_with_provider(
                provider_index=idx,
                user_message=user_message,
                current_context=current_data,
                conversation_history=conversation_history,
                schedule_list=schedule_list,
                memory_snippets=memory_snippets,
                contact_hints=contact_hints,
            )

            # Handle provider errors
            if "error" in result and len(result) == 1:
                results[_label] = {
                    "model": _model,
                    "error": result["error"],
                    "quality_score": 0,
                    "quality_notes": ["❌ 提供者失敗"],
                }
                print(f"[compare-models] {_label} ✗: {result['error'][:60]}")
                continue

            # Assess quality
            quality = _assess_response_quality(
                result, user_message, schedule_list, current_data
            )

            results[_label] = {
                "model": _model,
                "intent": result.get("intent"),
                "is_complete": result.get("is_complete"),
                "reply": result.get("reply", "")[:200],  # 限制長度
                "updated_data": result.get("updated_data", {}),
                "missing_fields": result.get("missing_fields", []),
                "quality_score": quality["score"],
                "quality_notes": quality["notes"],
            }
            print(f"[compare-models] {_label} ✓ (score: {quality['score']})")
        except Exception as e:
            results[_label] = {
                "model": _model,
                "error": str(e)[:100],
                "quality_score": 0,
                "quality_notes": ["❌ 異常"],
            }
            print(f"[compare-models] {_label} ✗: {str(e)[:60]}")

    # Compute consensus and ranking
    consensus = _compute_consensus(results)

    return {
        "user_message": user_message,
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "consensus": consensus,
        "best_model": max(
            [(k, v.get("quality_score", 0)) for k, v in results.items()],
            key=lambda x: x[1],
        )[0] if results else None,
        "total_models": len(results),
    }


def _assess_response_quality(result: dict, user_message: str, schedule_list: list, current_data: dict) -> dict:
    """
    Score response quality based on:
    - Completeness (is_complete flag)
    - Correctness (valid intent, no hallucinated schedule_id)
    - Helpfulness (appropriate next step)
    """
    score = 0
    notes = []

    # Check completeness
    if result.get("is_complete"):
        score += 30
        notes.append("✓ 決定完整")
    else:
        notes.append("⊘ 需要更多資訊")

    # Check intent validity
    intent = result.get("intent")
    if intent in ("create", "edit", "delete", "query"):
        score += 20
        notes.append(f"✓ Intent: {intent}")
    else:
        notes.append(f"✗ 不明 intent: {intent}")

    # For edit intent: check if schedule_id is valid
    if intent == "edit":
        target_id = result.get("target_schedule_id")
        valid_ids = {s.get("schedule_id") or s.get("id", "") for s in schedule_list}
        if target_id and target_id in valid_ids:
            score += 25
            notes.append(f"✓ 正確的 schedule_id")
        elif target_id:
            score -= 20
            notes.append(f"✗ 無效的 schedule_id: {target_id[:8]}")
        else:
            notes.append("⊘ 沒有 schedule_id")

    # Check for hallucinations in updated_data
    updated_data = result.get("updated_data", {})
    if updated_data:
        score += 15
        if _has_reasonable_data(updated_data):
            notes.append("✓ 合理的資料")
        else:
            notes.append("✗ 可疑的資料格式")
            score -= 10

    # Check reply quality
    reply = result.get("reply", "")
    if reply and len(reply) > 5:
        score += 10
        notes.append("✓ 有回覆訊息")
    elif not reply and not result.get("is_complete"):
        notes.append("⊘ 沒有回覆訊息")

    # Penalize empty responses that should have content
    if (not reply or not updated_data) and intent == "create" and result.get("is_complete"):
        score -= 15
        notes.append("✗ 完成但資料不足")

    return {
        "score": max(0, min(100, score)),
        "notes": notes,
    }


def _has_reasonable_data(data: dict) -> bool:
    """Check if updated_data has reasonable structure"""
    if not data:
        return False

    # Should have at least one meaningful field
    meaningful_fields = {"title", "start_time", "location", "participants"}
    has_field = any(k in data and data[k] for k in meaningful_fields)

    if not has_field:
        return False

    # Check date format if present
    if data.get("start_time"):
        try:
            datetime.fromisoformat(data["start_time"].replace("Z", "+00:00"))
        except Exception:
            return False

    return True


def _compute_consensus(results: dict) -> dict:
    """Analyze agreement between models"""
    if not results:
        return {"agreement_rate": 0, "consensus": "無結果"}

    valid_results = {k: v for k, v in results.items() if "error" not in v}
    if not valid_results:
        return {"agreement_rate": 0, "consensus": "所有模型都失敗"}

    # Check intent agreement
    intents = [v.get("intent") for v in valid_results.values()]
    intent_agreement = max(intents.count(i) for i in set(intents)) / len(intents) if intents else 0

    # Check is_complete agreement
    completes = [v.get("is_complete") for v in valid_results.values()]
    complete_agreement = (
        completes.count(True) / len(completes)
        if completes
        else 0
    )

    overall_agreement = (intent_agreement + complete_agreement) / 2

    return {
        "total_models": len(results),
        "successful_models": len(valid_results),
        "intent_agreement": round(intent_agreement, 2),
        "complete_agreement": round(complete_agreement, 2),
        "overall_agreement": round(overall_agreement, 2),
        "most_common_intent": max(set(intents), key=intents.count) if intents else None,
    }
