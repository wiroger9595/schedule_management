import sys
sys.path.append('/Users/chenrobert/Documents/code_life/schedule_management/server')

from app.models.schedule import Schedule
from datetime import datetime
import json

# Create a test schedule
schedule = Schedule(
    user_id="test_user",
    schedule_id="sch_test123",
    title="測試行程",
    description="這是一個測試",
    meeting_time="2026-02-12T15:00:00",
    meeting_location="信義區",
    status="P",
    transport_mode="car"
)

# Test dict() method
schedule_dict = schedule.dict()

print("Schedule dict() output:")
print(json.dumps(schedule_dict, indent=2, ensure_ascii=False, default=str))

# Check required fields
required_fields = ['id', 'title', 'start_time', 'location', 'status']
print("\n" + "="*60)
print("Checking required fields for frontend:")
for field in required_fields:
    if field in schedule_dict:
        print(f"✓ {field}: {schedule_dict[field]}")
    else:
        print(f"✗ {field}: MISSING")
