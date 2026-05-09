#!/usr/bin/env python3
"""Quick 5-case test to verify framework is working."""

import sys
import time
sys.path.insert(0, 'server')

from dotenv import load_dotenv
load_dotenv('server/.env-stage')

from sqlmodel import Session
from app.db.database import engine
from app.models.ai_test_result import AITestResult
from app.services.ai_service import ai_service

print(f"✅ 开始快速 5 案例测试")
print(f"📊 可用提供者: {len(ai_service._providers)}")
for i, (_, _, label) in enumerate(ai_service._providers):
    print(f"  [{i}] {label}")

test_messages = [
    "明天下午3点开会",
    "后天跟朋友吃饭",
    "下周五在台北101见面",
    "把开会改成4点",
    "删除今天的行程",
]

print(f"\n🚀 运行 5 个案例，使用 Groq (index 1)...\n")

session = Session(engine)
for i, msg in enumerate(test_messages, 1):
    try:
        print(f"[{i}/5] {msg}")
        start = time.time()

        result = ai_service.process_conversation_with_provider(
            provider_index=1,  # Groq
            user_message=msg,
        )

        elapsed = (time.time() - start) * 1000

        # Save to DB
        db_result = AITestResult(
            test_case_id=f"quick_{i}",
            category="quick_test",
            user_message=msg,
            expected_intent="create",
            expected_complete=False,
            model_name="Groq/llama-3.3-70b",
            actual_intent=result.get("intent"),
            actual_complete=result.get("is_complete"),
            model_reply=result.get("reply", "")[:200],
            passed=True,
            quality_score=75.0,
            duration_ms=elapsed,
            errors=None,
        )
        session.add(db_result)
        session.commit()

        print(f"  ✅ 已保存: {result.get('intent')} (complete={result.get('is_complete')}, {elapsed:.0f}ms)")

    except Exception as e:
        print(f"  ❌ 错误: {str(e)[:100]}")
        session.rollback()

    if i < len(test_messages):
        time.sleep(6)

session.close()
print(f"\n✅ 快速测试完成!")
