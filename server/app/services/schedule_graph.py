"""
Schedule creation state machine — plain Python replacement for LangGraph.

Nodes
─────
1. collect_info      – AI multi-turn conversation to gather title / time / location
2. validate_location – HERE + Nominatim scoring; asks user to pick when ambiguous
"""

from __future__ import annotations
from typing import List, Optional, TypedDict


class ScheduleState(TypedDict):
    # ── Inputs ──
    user_message: str
    conversation_history: List[dict]
    current_data: dict
    user_lat: Optional[float]
    user_lon: Optional[float]
    schedule_list: Optional[List[dict]]

    # ── AI node outputs ──
    updated_data: dict
    missing_fields: List[str]
    is_complete: bool
    reply: str
    intent: str
    target_schedule_id: Optional[str]
    needs_time_input: bool
    needs_location_input: bool

    # ── Location validation outputs ──
    location_result: Optional[dict]
    needs_location_confirm: bool
    location_candidates: List[dict]
    location_details: Optional[dict]
    location_not_found: bool


def collect_info_node(state: ScheduleState) -> ScheduleState:
    from .ai_service import ai_service
    current_data = state.get("current_data", {})
    session = current_data.pop("_session", None) if isinstance(current_data, dict) else None
    query_embedding = current_data.pop("_query_embedding", None) if isinstance(current_data, dict) else None
    byok_providers = current_data.pop("_byok_providers", None) if isinstance(current_data, dict) else None

    ai_result = ai_service.process_conversation(
        state["user_message"],
        current_data,
        conversation_history=state["conversation_history"],
        schedule_list=state.get("schedule_list"),
        session=session,
        query_embedding=query_embedding,
        providers=byok_providers,
    )
    return {
        **state,
        "updated_data": ai_result.get("updated_data", state["current_data"]),
        "missing_fields": ai_result.get("missing_fields", []),
        "is_complete": ai_result.get("is_complete", False),
        "reply": ai_result.get("reply", ""),
        "intent": ai_result.get("intent", "create"),
        "target_schedule_id": ai_result.get("target_schedule_id"),
        "needs_time_input": ai_result.get("needs_time_input", False),
        "needs_location_input": ai_result.get("needs_location_input", False),
    }


def validate_location_node(state: ScheduleState) -> ScheduleState:
    from .here_service import HereService
    location_name = state["updated_data"].get("location", "")

    loc_result = HereService.validate_location(
        location_name,
        lat=state.get("user_lat"),
        lon=state.get("user_lon"),
    )

    if loc_result["best"] is None:
        return {
            **state,
            "is_complete": False,
            "reply": f"找不到「{location_name}」，請直接輸入完整地址或更換地點名稱。",
            "needs_location_confirm": False,
            "location_candidates": [],
            "location_details": None,
            "location_result": loc_result,
            "location_not_found": True,
        }

    if loc_result["needs_selection"]:
        candidates_clean = [
            {
                "name": c.get("name") or c.get("address", "").split(",")[0].strip() or f"地點 {i+1}",
                "address": c.get("address", ""),
                "lat": c["lat"],
                "lon": c["lon"],
            }
            for i, c in enumerate(loc_result["candidates"])
            if c.get("name") or c.get("address")
        ]
        # Single candidate: route to confirm card instead of empty selection list
        if len(candidates_clean) == 1:
            single = candidates_clean[0]
            return {
                **state,
                "reply": f"我為您找到了「{single['name']}」（{single['address']}）。請問這個地點正確嗎？",
                "needs_location_confirm": True,
                "location_candidates": [],
                "location_details": single,
                "location_result": loc_result,
            }
        if candidates_clean:
            return {
                **state,
                "reply": f"我找到了幾個「{location_name}」相關的地點，請選擇正確的一個：",
                "needs_location_confirm": True,
                "location_candidates": candidates_clean,
                "location_details": None,
                "location_result": loc_result,
            }
        # All candidates had no name/address — fall through to not-found
        return {
            **state,
            "is_complete": False,
            "reply": f"找不到「{location_name}」，請直接輸入完整地址或更換地點名稱。",
            "needs_location_confirm": False,
            "location_candidates": [],
            "location_details": None,
            "location_result": loc_result,
            "location_not_found": True,
        }

    best = loc_result["best"]
    location_details = {
        "name": best["name"],
        "address": best["address"],
        "lat": best["lat"],
        "lon": best["lon"],
    }
    return {
        **state,
        "reply": f"我為您找到了「{location_details['name']}」（{location_details['address']}）。請問這個地點正確嗎？",
        "needs_location_confirm": True,
        "location_candidates": [],
        "location_details": location_details,
        "location_result": loc_result,
    }


class _ScheduleGraph:
    """Drop-in replacement for the compiled LangGraph StateGraph."""

    def invoke(self, state: dict) -> dict:
        # Ensure output fields have defaults
        state = {
            "needs_location_confirm": False,
            "location_candidates": [],
            "location_details": None,
            "location_result": None,
            "location_not_found": False,
            **state,
        }
        state = collect_info_node(state)
        intent = state.get("intent", "create")
        if intent == "create" and state["is_complete"] and state["updated_data"].get("location"):
            state = validate_location_node(state)
        return state


schedule_graph = _ScheduleGraph()
