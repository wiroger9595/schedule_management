import os
import sys

# Add server directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ai_service import ai_service

def test_case(name, message, context=None):
    print(f"\n--- Test: {name} ---")
    print(f"Message: {message}")
    result = ai_service.process_conversation(message, context or {})
    print(f"Is Complete: {result.get('is_complete')}")
    print(f"Missing Fields: {result.get('missing_fields')}")
    print(f"Participants: {result.get('updated_data', {}).get('participants')}")
    print(f"Reply: {result.get('reply')}")

if __name__ == '__main__':
    # Case 1: No contact mentioned
    test_case("No contact", "明天早上10點去台北101開會")
    
    # Case 2: Contact without @
    test_case("Contact without @", "明天早上10點和小明去台北101開會")
    
    # Case 3: Contact with @
    test_case("Contact with @", "明天早上10點和 @小明 去台北101開會")

    # Case 4: Follow up (Providing @ contact to an incomplete context)
    context = {
        "title": "開會",
        "start_time": "2026-03-02 10:00:00",
        "location": "台北101"
    }
    test_case("Follow up with @", "好，和 @小明", context)
