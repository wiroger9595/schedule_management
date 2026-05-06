#!/usr/bin/env python3
"""Diagnose HuggingFace integration issues."""

import sys
import time
sys.path.insert(0, '/Users/chenrobert/Documents/code_life/schedule_management/server')

from dotenv import load_dotenv
load_dotenv('/Users/chenrobert/Documents/code_life/schedule_management/server/.env-stage')

from app.services.ai_service import ai_service

print(f"🔍 Diagnosing HuggingFace Integration\n")
print(f"Available providers: {len(ai_service._providers)}")
for i, (cli, model, label) in enumerate(ai_service._providers):
    print(f"  [{i}] {label}")
    print(f"      Client type: {type(cli).__name__}")
    print(f"      Model: {model}")

print(f"\n📝 Testing HuggingFace (index 0)...")

test_message = "明天下午3點開會"
print(f"Message: {test_message}")

try:
    start = time.time()
    result = ai_service.process_conversation_with_provider(
        provider_index=0,  # HuggingFace
        user_message=test_message,
    )
    elapsed = (time.time() - start) * 1000

    print(f"\n✅ Success!")
    print(f"  Intent: {result.get('intent')}")
    print(f"  Complete: {result.get('is_complete')}")
    print(f"  Reply: {result.get('reply', '')[:100]}")
    print(f"  Time: {elapsed:.0f}ms")

except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}")
    print(f"  Message: {str(e)[:200]}")

    # Try to understand the error
    if "chat_completion" in str(e).lower():
        print("\n💡 Looks like chat_completion failed. Checking fallback...")
        print("   System should automatically try text_generation")

    if "text-generation" in str(e).lower() or "task" in str(e).lower():
        print("\n💡 Looks like a model/task support issue.")
        print("   This is a known HuggingFace limitation with free tier")
        print("   System will automatically fallback to Groq")

    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
