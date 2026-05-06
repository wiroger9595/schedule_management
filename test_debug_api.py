#!/usr/bin/env python3
"""
Simple test script for the debug/compare-models API.
Run this to test model comparison without needing a full auth token.
"""
import json
import sys
sys.path.insert(0, 'server')

from app.services.ai_service import ai_service
from app.services.prompt_builder import build_schedule_section

# Test data
user_message = "明天下午三點跟小明在信義區吃飯"
schedule_list = [
    {
        "schedule_id": "abc-123",
        "title": "跟Robert開會",
        "meeting_start_time": "2026-04-30T10:00:00",
        "meeting_location": "台北101",
        "is_owner": True,
    }
]
contact_hints = [
    {
        "nick_name": "小明",
        "similarity": 0.95,
        "comment": "朋友",
    }
]

print(f"🔍 Testing all {len(ai_service._providers)} models...")
print(f"📝 Input: {user_message}\n")

results = {}
for idx, (_cli, _model, _label) in enumerate(ai_service._providers):
    print(f"[{idx+1}/{len(ai_service._providers)}] Testing {_label}...", end=" ")
    try:
        result = ai_service.process_conversation_with_provider(
            provider_index=idx,
            user_message=user_message,
            schedule_list=schedule_list,
            contact_hints=contact_hints,
        )

        results[_label] = {
            "model": _model,
            "intent": result.get("intent", "?"),
            "is_complete": result.get("is_complete", False),
            "reply": result.get("reply", "")[:80],
            "updated_data": result.get("updated_data", {}),
        }
        print(f"✓ (intent: {result.get('intent')}, complete: {result.get('is_complete')})")
    except Exception as e:
        results[_label] = {"error": str(e)[:60]}
        print(f"✗ Error: {str(e)[:50]}")

# Display results
print("\n" + "="*80)
print("COMPARISON RESULTS")
print("="*80)

for label, data in results.items():
    print(f"\n🤖 {label}")
    if "error" in data:
        print(f"   ❌ {data['error']}")
    else:
        print(f"   Intent: {data['intent']}")
        print(f"   Complete: {data['is_complete']}")
        print(f"   Reply: {data['reply']}")
        if data["updated_data"]:
            print(f"   Data: {json.dumps(data['updated_data'], ensure_ascii=False, indent=6)}")

# Summary
print("\n" + "="*80)
successful = sum(1 for d in results.values() if "error" not in d)
print(f"📊 Summary: {successful}/{len(results)} models successful")

# Check consensus
intents = [d.get("intent") for d in results.values() if "error" not in d]
if intents:
    most_common = max(set(intents), key=intents.count)
    agreement = intents.count(most_common) / len(intents)
    print(f"🎯 Intent consensus: {most_common} ({int(agreement*100)}% agreement)")

    if agreement >= 0.8:
        print("✓ Models agree on intent")
    else:
        print("⚠️  Models have different opinions")
