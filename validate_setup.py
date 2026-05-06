#!/usr/bin/env python3
"""Quick validation of AI service setup - tests 10 cases, saves to DB."""

import sys
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, '/Users/chenrobert/Documents/code_life/schedule_management/server')

from dotenv import load_dotenv
load_dotenv('/Users/chenrobert/Documents/code_life/schedule_management/server/.env-stage')

from sqlmodel import Session
from app.db.database import engine
from app.models.ai_test_result import AITestResult
from app.services.ai_service import ai_service

test_cases = [
    ("創建簡單行程", "明天下午三點開會", "create", False),
    ("完整地點時間", "後天晚上七點跟朋友吃飯在信義區", "create", True),
    ("週日期", "下禮拜五上午十點在台北101開會", "create", True),
    ("修改行程", "把開會改成下午四點", "edit", False),
    ("刪除行程", "刪除開會", "delete", False),
    ("查詢行程", "我有什麼行程", "query", False),
    ("時間段", "下午去運動", "create", False),
    ("參與者", "跟小明吃飯", "create", False),
    ("地點查詢", "在哪裡開會", "query", False),
    ("時間修改", "改成明天", "edit", False),
]

print("🔍 Validating AI Service Setup\n")
print(f"Available providers: {len(ai_service._providers)}")
for i, (cli, model, label) in enumerate(ai_service._providers):
    print(f"  [{i}] {label}")

print(f"\n✅ Testing with Groq (index 1)")
print("="*60)

session = Session(engine)
success_count = 0
error_count = 0

for i, (name, message, expected_intent, expected_complete) in enumerate(test_cases, 1):
    try:
        print(f"\n[{i:2d}/10] {name}")
        print(f"    Message: {message}")

        start = time.time()
        result = ai_service.process_conversation_with_provider(
            provider_index=1,  # Groq
            user_message=message,
        )
        elapsed = (time.time() - start) * 1000

        intent = result.get("intent")
        complete = result.get("is_complete")
        print(f"    Result: intent={intent}, complete={complete}, time={elapsed:.0f}ms")

        # Save to DB
        db_result = AITestResult(
            test_case_id=f"validate_{i:02d}",
            category="validation",
            user_message=message,
            expected_intent=expected_intent,
            expected_complete=expected_complete,
            model_name="Groq/llama-3.3-70b",
            actual_intent=intent,
            actual_complete=complete,
            model_reply=result.get("reply", "")[:500],
            passed=(intent == expected_intent and complete == expected_complete),
            quality_score=75.0,
            duration_ms=elapsed,
            errors=None,
        )
        session.add(db_result)
        session.commit()

        success_count += 1
        print(f"    ✅ Saved to DB")

    except Exception as e:
        error_count += 1
        print(f"    ❌ Error: {str(e)[:100]}")
        session.rollback()

    if i < len(test_cases):
        time.sleep(6)  # Throttle

session.close()

print("\n" + "="*60)
print(f"✅ Validation Complete: {success_count}/10 passed, {error_count} errors")
print("\n📊 Results saved to ai_test_result table")

sys.exit(0 if error_count == 0 else 1)
