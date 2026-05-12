#!/usr/bin/env python3
"""
彈性 90-test 執行器：
  python run_test_v2.py --provider cerebras --n 90      # 全跑
  python run_test_v2.py --provider groq --n 20          # 跑前 20 個
  python run_test_v2.py --provider cerebras --no-rag    # 不用 RAG（基準）
  python run_test_v2.py --provider cerebras --rag       # 用 RAG（強化）
"""

import argparse
import sys
import time
sys.path.insert(0, 'server')

from dotenv import load_dotenv
load_dotenv('server/.env')

from sqlmodel import Session
from app.db.database import engine
from app.models.ai_test_result import AITestResult
from app.services.ai_service import ai_service
from optimize_ai_assistant import AIAssistantTester

PROVIDER_MAP = {
    "cerebras": 0,
    "gemini": 1,
    "huggingface": 2,
    "hf": 2,
    "groq": 3,
    "openrouter-qwen": 4,
    "qwen": 4,
    "openrouter-deepseek": 5,
    "deepseek": 5,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="cerebras",
                        choices=list(PROVIDER_MAP.keys()))
    parser.add_argument("--n", type=int, default=90, help="number of tests to run")
    parser.add_argument("--rag", action="store_true", default=True,
                        help="use RAG (default True)")
    parser.add_argument("--no-rag", action="store_false", dest="rag",
                        help="disable RAG for baseline comparison")
    parser.add_argument("--throttle", type=float, default=0.3,
                        help="seconds between tests")
    args = parser.parse_args()

    provider_idx = PROVIDER_MAP[args.provider]
    _, _, label = ai_service._providers[provider_idx]
    rag_label = "with RAG" if args.rag else "no RAG (baseline)"

    tester = AIAssistantTester()
    test_cases = tester.test_cases[:args.n]
    print(f"📊 Running {len(test_cases)} tests with {label} | {rag_label}\n")

    session = Session(engine)
    rag_session = session if args.rag else None

    passed = 0
    failed = 0
    errors = 0
    start_total = time.time()

    for i, tc in enumerate(test_cases, 1):
        try:
            start = time.time()
            result = ai_service.process_conversation_with_provider(
                provider_index=provider_idx,
                user_message=tc.user_message,
                schedule_list=tc.schedule_list,
                contact_hints=tc.contact_hints,
                session=rag_session,
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

                # Save (with RAG label so we can compare runs)
                model_label = f"{label}{'+RAG' if args.rag else ''}"
                db_result = AITestResult(
                    test_case_id=tc.id,
                    category=tc.category,
                    user_message=tc.user_message,
                    expected_intent=tc.expected_intent,
                    expected_complete=tc.expected_complete,
                    model_name=model_label,
                    actual_intent=actual_intent,
                    actual_complete=actual_complete,
                    model_reply=(result.get("reply", "") or "")[:500],
                    passed=test_passed,
                    quality_score=75.0 if test_passed else 30.0,
                    duration_ms=elapsed,
                    errors=None,
                )
                session.add(db_result)
                session.commit()

            print(f"[{i:2d}/{len(test_cases)}] {status} {tc.name[:30]:30s} ({elapsed:.0f}ms) intent={actual_intent}")
        except Exception as e:
            errors += 1
            print(f"[{i:2d}/{len(test_cases)}] 💥 {tc.name[:30]:30s} ERROR: {str(e)[:60]}")
            session.rollback()

        time.sleep(args.throttle)

    session.close()
    total = len(test_cases)
    elapsed_total = time.time() - start_total
    pct = passed * 100 // total if total else 0
    print(f"\n{'='*60}")
    print(f"完成 ({elapsed_total:.0f}秒) | {label} | {rag_label}")
    print(f"通过: {passed}/{total} ({pct}%) | 失败: {failed} | ERROR: {errors}")


if __name__ == "__main__":
    main()
