#!/usr/bin/env python3
"""Direct Groq 90-test runner."""

import sys
import time
sys.path.insert(0, 'server')

from dotenv import load_dotenv
load_dotenv('server/.env-stage')

from sqlmodel import Session
from app.db.database import engine
from app.models.ai_test_result import AITestResult
from app.services.ai_service import ai_service

from optimize_ai_assistant import AIAssistantTester

def main():
    tester = AIAssistantTester()
    test_cases = tester.test_cases
    print(f"📊 Loaded {len(test_cases)} test cases")

    # Find Groq index
    groq_idx = next((i for i, (_,_,l) in enumerate(ai_service._providers) if 'Groq' in l), None)
    if groq_idx is None:
        print("❌ Groq not found!")
        return

    print(f"🤖 Provider: Groq (index {groq_idx})")
    print(f"🚀 Starting 90 tests...\n")

    session = Session(engine)
    passed = 0
    failed = 0
    errors = 0
    start_total = time.time()

    for i, tc in enumerate(test_cases, 1):
        try:
            start = time.time()
            result = ai_service.process_conversation_with_provider(
                provider_index=groq_idx,
                user_message=tc.user_message,
                schedule_list=tc.schedule_list,
                contact_hints=tc.contact_hints,
            )
            elapsed = (time.time() - start) * 1000

            actual_intent = result.get("intent", "?")
            actual_complete = result.get("is_complete", False)

            if actual_intent == "ERROR":
                errors += 1
                status = "💥"
            else:
                test_passed = (actual_intent == tc.expected_intent and
                               actual_complete == tc.expected_complete)
                if test_passed:
                    passed += 1
                    status = "✅"
                else:
                    failed += 1
                    status = "❌"

                db_result = AITestResult(
                    test_case_id=tc.id,
                    category=tc.category,
                    user_message=tc.user_message,
                    expected_intent=tc.expected_intent,
                    expected_complete=tc.expected_complete,
                    model_name="Groq/llama-3.3-70b",
                    actual_intent=actual_intent,
                    actual_complete=actual_complete,
                    model_reply=result.get("reply", "")[:500],
                    passed=test_passed,
                    quality_score=75.0 if test_passed else 30.0,
                    duration_ms=elapsed,
                    errors=None,
                )
                session.add(db_result)
                session.commit()

            print(f"[{i:2d}/90] {status} {tc.name[:30]:30s} ({elapsed:.0f}ms) intent={actual_intent}")

        except Exception as e:
            errors += 1
            print(f"[{i:2d}/90] 💥 {tc.name[:30]:30s} ERROR: {str(e)[:60]}")
            session.rollback()

        # Groq: 2秒 throttle (每分钟 30 = 1 req per 2s)
        time.sleep(2.5)

    session.close()
    total_elapsed = time.time() - start_total
    print(f"\n{'='*60}")
    print(f"✅ 测试完成! 总时长: {total_elapsed:.0f}秒")
    print(f"📊 通过: {passed}/{len(test_cases)} ({passed*100//len(test_cases)}%)")
    print(f"📊 失败: {failed}, 错误: {errors}")

if __name__ == "__main__":
    main()
