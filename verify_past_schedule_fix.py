#!/usr/bin/env python3
"""
Quick verification: re-run only the 8 past_schedule test cases against
Cerebras with RAG to see if the fix improves the pass rate.

Usage:
    python verify_past_schedule_fix.py
"""
import sys
import time

sys.path.insert(0, "server")

from dotenv import load_dotenv
load_dotenv("server/.env")

from sqlmodel import Session
from app.db.database import engine
from app.models.ai_test_result import AITestResult
from app.services.ai_service import ai_service
from optimize_ai_assistant import AIAssistantTester


def main():
    tester = AIAssistantTester()
    cases = [tc for tc in tester.test_cases if tc.category == "past_schedule"]
    print(f"Found {len(cases)} past_schedule test cases\n")

    session = Session(engine)
    passed = failed = errors = 0
    fails = []

    for i, tc in enumerate(cases, 1):
        try:
            t0 = time.time()
            result = ai_service.process_conversation_with_provider(
                provider_index=0,  # Cerebras
                user_message=tc.user_message,
                schedule_list=tc.schedule_list,
                contact_hints=tc.contact_hints,
                session=session,  # RAG enabled
            )
            elapsed_ms = (time.time() - t0) * 1000

            actual_intent = result.get("intent", "?")
            actual_complete = result.get("is_complete", False)

            if actual_intent == "ERROR":
                errors += 1
                status = "💥"
            else:
                test_passed = (
                    actual_intent == tc.expected_intent
                    and actual_complete == tc.expected_complete
                )
                if test_passed:
                    passed += 1
                    status = "✅"
                else:
                    failed += 1
                    status = "❌"
                    fails.append(
                        f"  - {tc.id} | {tc.user_message[:40]}\n"
                        f"      expected: intent={tc.expected_intent}, complete={tc.expected_complete}\n"
                        f"      actual:   intent={actual_intent}, complete={actual_complete}\n"
                        f"      reply:    {(result.get('reply') or '')[:100]}"
                    )

                db_result = AITestResult(
                    test_case_id=tc.id,
                    category=tc.category,
                    user_message=tc.user_message,
                    expected_intent=tc.expected_intent,
                    expected_complete=tc.expected_complete,
                    model_name="Cerebras/qwen-3-235b+RAG",
                    actual_intent=actual_intent,
                    actual_complete=actual_complete,
                    model_reply=(result.get("reply", "") or "")[:500],
                    passed=test_passed,
                    quality_score=75.0 if test_passed else 30.0,
                    duration_ms=elapsed_ms,
                    errors=None,
                )
                session.add(db_result)
                session.commit()

            print(f"[{i}/{len(cases)}] {status} {tc.id:8s} {tc.user_message[:40]} ({elapsed_ms:.0f}ms)")
        except Exception as e:
            errors += 1
            session.rollback()
            print(f"[{i}/{len(cases)}] 💥 {tc.id}: {str(e)[:80]}")
        time.sleep(3)  # throttle to avoid Cerebras rate limit

    session.close()

    print(f"\n{'='*60}")
    print(f"past_schedule: ✅{passed} / ❌{failed} / 💥{errors}")
    rate_excl_err = passed * 100 // (passed + failed) if (passed + failed) else 0
    print(f"pass rate (excl. errors): {passed}/{passed+failed} = {rate_excl_err}%")

    if fails:
        print("\nFailures:")
        for f in fails:
            print(f)


if __name__ == "__main__":
    main()
