import sys
sys.path.append('/Users/chenrobert/Documents/code_life/schedule_management/server')

from app.services.gemini_service import gemini_service

# Test the schedule extraction
test_message = "明天下午3點跟Robert在信義區吃飯"

print(f"Testing schedule extraction with message: {test_message}")
print("-" * 60)

try:
    result = gemini_service.extract_schedule_info(test_message)
    print("✓ Schedule extraction successful!")
    print("\nExtracted data:")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n" + "-" * 60)
    print("Confirmation message:")
    print(gemini_service.generate_confirmation_message(result))
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
