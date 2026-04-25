"""
AI Regression Test Suite
────────────────────────
Catches prompt regressions automatically. Run after every prompt change:

    cd server && python -m pytest tests/test_ai_regression.py -v

Each test case:
  - calls ai_service.process_conversation directly (no HTTP, no DB)
  - asserts the specific behavior that was once broken

Adding a new case:
  1. Find the failing scenario in production logs
  2. Copy the user_message + schedule_list + context
  3. Write an assertion for the correct output
  4. The test prevents that exact error from ever coming back
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.ai_service import ai_service

# ── Shared fixture: a realistic schedule list ────────────────────────────────
SCHEDULES = [
    {
        "id": "se956cee1a02b74e479012fc523d067461",
        "title": "與文哥開會",
        "start_time": "2026-05-10T10:00:00",
        "location": "新竹巨城",
    },
    {
        "id": "seabc123def456abc123def456abc12345",
        "title": "打球",
        "start_time": "2026-05-12T15:00:00",
        "location": "新竹體育館",
    },
    {
        "id": "se999000111222333444555666777888ab",
        "title": "與Robert吃飯",
        "start_time": "2026-05-15T19:00:00",
        "location": "台北信義區",
    },
]


def call(user_message, context=None, history=None, schedules=None):
    return ai_service.process_conversation(
        user_message=user_message,
        current_context=context or {},
        conversation_history=history or [],
        schedule_list=schedules if schedules is not None else SCHEDULES,
    )


# ════════════════════════════════════════════════════════════════════════════
# Group 1: schedule_id must come from the list
# ════════════════════════════════════════════════════════════════════════════

class TestScheduleIdValidation:
    def test_edit_returns_id_from_list(self):
        r = call("把與文哥開會的時間改成下午三點")
        if r["intent"] == "edit":
            assert r["target_schedule_id"] in {s["id"] for s in SCHEDULES}, (
                f"AI returned schedule_id={r['target_schedule_id']!r} which is not in the list"
            )

    def test_delete_returns_id_from_list(self):
        r = call("刪掉打球的行程")
        if r["intent"] == "delete":
            assert r["target_schedule_id"] in {s["id"] for s in SCHEDULES}, (
                f"AI returned schedule_id={r['target_schedule_id']!r} which is not in the list"
            )

    def test_empty_schedule_list_does_not_hallucinate_id(self):
        r = call("把那個行程改掉", schedules=[])
        # With empty list, should ask user or return is_complete=False
        assert r.get("is_complete") is False, "Should not complete edit when schedule list is empty"

    def test_vague_edit_triggers_ask(self):
        """'改一下行程' with no clear target should ask user, not hallucinate an id."""
        r = call("改一下行程")
        # Either ask_user (is_complete=False, no schedule_id) or lists schedules in reply
        assert r.get("is_complete") is False
        assert r.get("target_schedule_id") is None or r.get("target_schedule_id") in {s["id"] for s in SCHEDULES}


# ════════════════════════════════════════════════════════════════════════════
# Group 2: edit intent — only changed fields included
# ════════════════════════════════════════════════════════════════════════════

class TestEditFieldPurity:
    def test_time_only_edit_no_location(self):
        """User says 'change time to 3pm' — location must NOT be included."""
        r = call(
            "下午三點",
            context={"_pending_edit_schedule_id": SCHEDULES[0]["id"]},
        )
        if r["intent"] == "edit" and r.get("is_complete"):
            updated = r.get("updated_data", {})
            assert "location" not in updated or updated.get("location") is None, (
                "Changing only time should not include location in updated_data"
            )

    def test_update_schedule_has_at_least_one_field(self):
        """update_schedule must always have at least one changed field."""
        r = call("把與文哥開會的行程改一下", context={})
        if r["intent"] == "edit" and r.get("is_complete"):
            updated = r.get("updated_data", {})
            meaningful = {k: v for k, v in updated.items()
                          if k not in ("schedule_id",) and v is not None}
            assert meaningful, "update_schedule returned with no changed fields"


# ════════════════════════════════════════════════════════════════════════════
# Group 3: ambiguity → list schedules
# ════════════════════════════════════════════════════════════════════════════

class TestAmbiguityHandling:
    def test_multiple_matches_triggers_list(self):
        """Two schedules in 新竹 — AI should ask user to choose, not pick silently."""
        r = call("修改新竹的行程")
        # Should not auto-complete the edit
        assert r.get("is_complete") is False or r.get("target_schedule_id") is None, (
            "Ambiguous target should not auto-complete"
        )

    def test_no_match_triggers_list_not_error(self):
        """If described schedule doesn't match any, reply should guide user, not crash."""
        r = call("修改跟小美的行程")  # 小美 not in schedule list
        assert r.get("is_complete") is False
        assert r.get("reply"), "Should always return a reply string"


# ════════════════════════════════════════════════════════════════════════════
# Group 4: create intent — required fields
# ════════════════════════════════════════════════════════════════════════════

class TestCreateRequiredFields:
    def test_missing_time_triggers_ask(self):
        r = call("跟Robert吃飯，在信義區")
        # No time given → must ask
        assert r.get("is_complete") is False, "Should not create without time"

    def test_missing_location_triggers_ask(self):
        r = call("明天下午三點跟小明吃飯")
        assert r.get("is_complete") is False, "Should not create without location"

    def test_full_info_creates(self):
        r = call("明天下午三點跟Robert在信義星巴克吃飯")
        # Should either create (is_complete=True) or ask about chain-store branch
        assert r.get("reply"), "Should always reply"


# ════════════════════════════════════════════════════════════════════════════
# Group 5: context continuity (pending edit)
# ════════════════════════════════════════════════════════════════════════════

class TestContextContinuity:
    def test_pending_edit_uses_stored_id(self):
        """When _pending_edit_schedule_id is in context, next reply should use it."""
        sid = SCHEDULES[0]["id"]
        r = call(
            "改成下午五點",
            context={"_pending_edit_schedule_id": sid},
        )
        assert r.get("intent") == "edit", "Should remain in edit intent"
        assert r.get("target_schedule_id") == sid, (
            f"Should use stored schedule_id={sid!r}, got {r.get('target_schedule_id')!r}"
        )

    def test_pending_edit_does_not_create(self):
        """With pending edit context, reply must NOT call create_schedule."""
        sid = SCHEDULES[1]["id"]
        r = call(
            "新竹關埔門市",
            context={"_pending_edit_schedule_id": sid, "location": "新竹體育館"},
        )
        assert r.get("intent") != "create" or r.get("is_complete") is False, (
            "Should not create a new schedule when pending edit exists"
        )


# ════════════════════════════════════════════════════════════════════════════
# Group 6: non-schedule queries
# ════════════════════════════════════════════════════════════════════════════

class TestOffTopicHandling:
    def test_weather_query_redirected(self):
        r = call("今天天氣怎樣")
        assert r.get("reply"), "Should always reply"
        assert r.get("is_complete") is False

    def test_list_schedules_returns_reply(self):
        r = call("我有什麼行程")
        assert r.get("reply"), "Should list schedules"
        assert r.get("is_complete") is False  # listing is not a create/edit action


if __name__ == "__main__":
    # Quick smoke-test without pytest
    import traceback
    passed, failed = 0, 0
    suites = [
        TestScheduleIdValidation, TestEditFieldPurity,
        TestAmbiguityHandling, TestCreateRequiredFields,
        TestContextContinuity, TestOffTopicHandling,
    ]
    for suite_cls in suites:
        suite = suite_cls()
        for name in [m for m in dir(suite) if m.startswith("test_")]:
            try:
                getattr(suite, name)()
                print(f"  ✅  {suite_cls.__name__}.{name}")
                passed += 1
            except AssertionError as e:
                print(f"  ❌  {suite_cls.__name__}.{name}: {e}")
                failed += 1
            except Exception as e:
                print(f"  💥  {suite_cls.__name__}.{name}: {e}")
                traceback.print_exc()
                failed += 1
    print(f"\n{'='*50}")
    print(f"Passed: {passed}  Failed: {failed}")
    sys.exit(1 if failed else 0)
