#!/usr/bin/env python3
"""Test DB saving with a few test cases."""

import os
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

def test_and_save_one():
    """Test one case and save to DB."""
    user_message = "明天下午三點在台北101開會"

    print(f"[TEST] Message: {user_message}")
    print(f"[TEST] Available providers: {len(ai_service._providers)}")

    # Use Groq (index 1 should be Groq)
    for idx, (cli, model, label) in enumerate(ai_service._providers):
        print(f"  [{idx}] {label}")

    try:
        result = ai_service.process_conversation_with_provider(
            provider_index=1,  # Groq
            user_message=user_message,
        )

        print(f"\n[RESULT]")
        print(f"  Intent: {result.get('intent')}")
        print(f"  Complete: {result.get('is_complete')}")
        print(f"  Reply: {result.get('reply')}")

        # Try to save to DB
        print(f"\n[SAVING TO DB]")
        session = Session(engine)

        db_result = AITestResult(
            test_case_id="test_1",
            category="parsing",
            user_message=user_message,
            expected_intent="create",
            expected_complete=False,
            model_name="Groq/llama-3.3-70b",
            actual_intent=result.get("intent"),
            actual_complete=result.get("is_complete"),
            model_reply=result.get("reply", "")[:500],
            passed=result.get("intent") == "create",
            quality_score=75.0,
            duration_ms=100.0,
            errors=None,
        )

        session.add(db_result)
        session.commit()
        session.close()

        print(f"✅ Saved to DB successfully")
        return True
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_and_save_one()
    sys.exit(0 if success else 1)
