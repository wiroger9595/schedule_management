#!/usr/bin/env python3
"""Quick test to verify HuggingFace Mistral integration works."""

import os
import sys
import json

# Add server to path
sys.path.insert(0, '/Users/chenrobert/Documents/code_life/schedule_management/server')

from dotenv import load_dotenv
load_dotenv('/Users/chenrobert/Documents/code_life/schedule_management/server/.env-stage')

from app.services.ai_service import AIService

def test_hf_single_case():
    """Test a single AI call with HuggingFace."""
    ai_service = AIService()

    # Simple test case: 創建行程
    user_message = "幫我排一個行程，下午3點在台北101跟朋友見面"

    print(f"[TEST] Testing: {user_message}")
    print(f"[TEST] Provider cascade: {len(ai_service._providers)} providers")

    try:
        result = ai_service.process_conversation(user_message)
        print(f"\n[SUCCESS] Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return True
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_hf_single_case()
    sys.exit(0 if success else 1)
