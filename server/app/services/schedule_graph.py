"""
LangGraph-based schedule creation state machine.

Nodes
─────
1. collect_info      – AI multi-turn conversation to gather title / time / location
2. validate_location – HERE + Nominatim scoring; asks user to pick when ambiguous

The graph returns a rich ScheduleState dict that the chat endpoint
interprets to decide whether to show a location picker, ask more questions,
or proceed to DB creation.

DB conflict-check and schedule creation stay in the endpoint (they need the
FastAPI session dependency and are not part of the AI reasoning loop).
"""

from __future__ import annotations

from typing import List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from .ai_service import ai_service
from .here_service import HereService


# ─────────────────────────── State schema ────────────────────────────────────

class ScheduleState(TypedDict):
    # ── Inputs ──
    user_message: str
    conversation_history: List[dict]
    current_data: dict
    user_lat: Optional[float]
    user_lon: Optional[float]
    schedule_list: Optional[List[dict]]  # user's existing schedules for edit/delete

    # ── AI node outputs ──
    updated_data: dict
    missing_fields: List[str]
    is_complete: bool
    reply: str
    intent: str                          # create | edit | delete
    target_schedule_id: Optional[str]    # for edit/delete

    # ── Location validation outputs ──
    location_result: Optional[dict]
    needs_location_confirm: bool
    location_candidates: List[dict]    # non-empty → show candidate list
    location_details: Optional[dict]   # non-None → show single-confirm card


# ─────────────────────────── Node: collect_info ───────────────────────────────

def collect_info_node(state: ScheduleState) -> ScheduleState:
    """Call the AI to extract / update schedule fields from the latest message."""
    ai_result = ai_service.process_conversation(
        state["user_message"],
        state["current_data"],
        conversation_history=state["conversation_history"],
        schedule_list=state.get("schedule_list"),
    )
    return {
        **state,
        "updated_data": ai_result.get("updated_data", state["current_data"]),
        "missing_fields": ai_result.get("missing_fields", []),
        "is_complete": ai_result.get("is_complete", False),
        "reply": ai_result.get("reply", ""),
        "intent": ai_result.get("intent", "create"),
        "target_schedule_id": ai_result.get("target_schedule_id"),
    }


# ─────────────────────────── Node: validate_location ─────────────────────────

def validate_location_node(state: ScheduleState) -> ScheduleState:
    """
    Score HERE + Nominatim results by name similarity.
    • No results  → set is_complete=False, ask user to clarify
    • Multiple candidates (needs_selection) → return candidate list
    • Single high-confidence match → return location_details for quick confirm
    """
    location_name = state["updated_data"].get("location", "")

    loc_result = HereService.validate_location(
        location_name,
        lat=state.get("user_lat"),
        lon=state.get("user_lon"),
    )

    # ── No results at all ──
    if loc_result["best"] is None:
        return {
            **state,
            "is_complete": False,
            "reply": f"抱歉，找不到「{location_name}」相關的地點，請問可以提供更詳細的地址或地標名稱嗎？",
            "needs_location_confirm": False,
            "location_candidates": [],
            "location_details": None,
            "location_result": loc_result,
        }

    # ── Multiple plausible matches ──
    if loc_result["needs_selection"]:
        candidates_clean = [
            {
                "name": c["name"],
                "address": c["address"],
                "lat": c["lat"],
                "lon": c["lon"],
            }
            for c in loc_result["candidates"]
        ]
        return {
            **state,
            "reply": f"我找到了幾個「{location_name}」相關的地點，請選擇正確的一個：",
            "needs_location_confirm": True,
            "location_candidates": candidates_clean,
            "location_details": None,
            "location_result": loc_result,
        }

    # ── Single high-confidence match ──
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


# ─────────────────────────── Routing ─────────────────────────────────────────

def route_after_collect(state: ScheduleState) -> str:
    """Run location validation only for create intent when all fields are collected."""
    intent = state.get("intent", "create")
    if intent == "create" and state["is_complete"] and state["updated_data"].get("location"):
        return "validate_location"
    return END


# ─────────────────────────── Graph assembly ──────────────────────────────────

def _build_graph() -> StateGraph:
    g = StateGraph(ScheduleState)

    g.add_node("collect_info", collect_info_node)
    g.add_node("validate_location", validate_location_node)

    g.set_entry_point("collect_info")
    g.add_conditional_edges("collect_info", route_after_collect)
    g.add_edge("validate_location", END)

    return g.compile()


schedule_graph = _build_graph()
