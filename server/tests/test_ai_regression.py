"""
AI Regression Test Suite
────────────────────────
Catches prompt regressions automatically. Run after every prompt change:

    cd server && python -m pytest tests/test_ai_regression.py -v

Case 內容在 tests/ai_cases.py —— 這支跑預設 cascade（等同 production），
run_conformance.py 拿同一份 case 跑每一個 provider 做跨模型比較。
改 case 只改 ai_cases.py 一個地方。

Adding a new case:
  1. Find the failing scenario in production logs
  2. Add a dict to CASES in tests/ai_cases.py
  3. 寫進 expect_intent / expect_complete / check，不要寫條件式斷言
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.ai_service import ai_service
from tests.ai_cases import CASES, case_schedules, evaluate

# Cerebras 免費 tier 是 5 RPM，而且現在 cascade 後面幾家全是死的（Gemini 模型
# 下架、Groq key 失效、OpenRouter 沒 credit），撞到限流就沒有備援可接。
# 不節流的話這 15 個 case 會有一半是被限流打掉的假失敗。
_MIN_INTERVAL = float(os.getenv("AI_TEST_MIN_INTERVAL", "12.5"))
_last_call_at = [0.0]


@pytest.fixture(autouse=True)
def _throttle():
    wait = _MIN_INTERVAL - (time.time() - _last_call_at[0])
    if wait > 0:
        time.sleep(wait)
    _last_call_at[0] = time.time()


def run_case(case: dict) -> dict:
    # context 要複製 —— process_conversation 會 pop 掉 _pre_intent 之類的 key
    return ai_service.process_conversation(
        user_message=case["message"],
        current_context=dict(case.get("context") or {}),
        conversation_history=[],
        schedule_list=case_schedules(case),
    )


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case(case):
    result = run_case(case)
    passed, score, errors = evaluate(case, result)
    assert passed, (
        f"\n  case:    {case['id']} ({case['category']})"
        f"\n  message: {case['message']!r}"
        f"\n  score:   {score:.2f}"
        f"\n  errors:  " + "\n           ".join(errors) +
        f"\n  reply:   {(result.get('reply') or '')[:120]!r}"
    )
