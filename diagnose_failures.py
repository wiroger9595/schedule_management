#!/usr/bin/env python3
"""
Diagnose why test failures are happening.
Run a few key test cases with detailed debugging output.
"""
import sys
sys.path.insert(0, "server")

from optimize_ai_assistant import AIAssistantTester, TestCase
from app.services.ai_service import ai_service

def diagnose():
    """Run 5 basic tests with detailed output"""
    tester = AIAssistantTester()

    # Pick a few representative test cases
    test_ids = ["parse_2", "intent_1", "location_1", "past_1", "edge_1"]
    tests_to_run = [tc for tc in tester.test_cases if tc.id in test_ids]

    print("🔍 AI 行程助理 - 失敗診斷\n")
    print(f"模型: {[l for _, _, l in ai_service._providers]}\n")
    print("="*80)

    for test in tests_to_run:
        print(f"\n📝 測試: {test.id} - {test.name}")
        print(f"   輸入: {test.user_message}")
        print(f"   預期: intent={test.expected_intent}, complete={test.expected_complete}")
        print(f"\n   執行結果:")

        # Run on first available model
        try:
            result = ai_service.process_conversation_with_provider(
                provider_index=0,
                user_message=test.user_message,
                schedule_list=test.schedule_list,
                contact_hints=test.contact_hints,
            )

            print(f"   ✓ 模型回應:")
            print(f"     intent: {result.get('intent')}")
            print(f"     is_complete: {result.get('is_complete')}")
            print(f"     reply: {result.get('reply', '')[:80]}")
            print(f"     updated_data keys: {list(result.get('updated_data', {}).keys())}")

            # Check what went wrong
            failures = []
            if result.get('intent') != test.expected_intent:
                failures.append(f"❌ Intent 不符: 期望 {test.expected_intent}, 得到 {result.get('intent')}")
            if result.get('is_complete') != test.expected_complete:
                failures.append(f"❌ Complete 不符: 期望 {test.expected_complete}, 得到 {result.get('is_complete')}")

            if failures:
                print(f"\n   失敗原因:")
                for f in failures:
                    print(f"     {f}")
            else:
                print(f"\n   ✅ 通過!")

        except Exception as e:
            print(f"   ❌ 錯誤: {str(e)[:100]}")

        print("-"*80)


def analyze_prompt_issue():
    """Analyze if it's a prompt issue"""
    print("\n\n" + "="*80)
    print("🔎 prompt 分析")
    print("="*80)

    from app.services.prompt_builder import build_system_prompt
    from datetime import datetime, timedelta, timezone

    TAIPEI_TZ = timezone(timedelta(hours=8))
    today = datetime.now(tz=TAIPEI_TZ)

    # Check what system prompt looks like
    system_prompt = build_system_prompt(today, "【行程清單】(無)", "", "")

    print("\n📋 System Prompt 長度:", len(system_prompt), "字元")
    print("\n🔍 Prompt 關鍵部分:")

    # Extract key sections
    lines = system_prompt.split('\n')
    for i, line in enumerate(lines[:30]):
        print(f"  {i+1:2d}. {line[:70]}")

    print("\n... (中間省略) ...\n")

    for i, line in enumerate(lines[-10:]):
        print(f"  {len(lines)-10+i+1:2d}. {line[:70]}")


if __name__ == "__main__":
    print("⚠️  這個診斷工具會在控制台輸出詳細結果\n")

    diagnose()
    analyze_prompt_issue()

    print("\n\n" + "="*80)
    print("💡 根據上面的輸出，檢查:")
    print("="*80)
    print("""
1. Intent 辨識:
   - 模型是否正確理解 create/edit/delete/query?
   - 或者總是回傳相同的 intent?

2. Complete 判斷:
   - 模型是否過度樂觀 (認為完整)?
   - 還是過度悲觀 (認為不完整)?

3. Reply 質量:
   - 是否回覆內容為空?
   - 是否有 error?

4. 如果都失敗，可能問題:
   a) API Key 有問題
   b) Model 推理能力有限
   c) System Prompt 不夠清楚
   d) 測試用例預期設置錯誤

建議下一步:
- 查看詳細的 HTML 報告
- 提供具體的失敗案例
- 檢查環境變數和 API key
""")
