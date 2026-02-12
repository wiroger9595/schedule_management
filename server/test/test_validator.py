from app.utils.text_validator import validate_schedule_message

test_cases = [
    ("明天下午3點去開會", True),
    ("下週一聚餐", True),
    ("2月14號情人節", True),
    ("你好", False),
    ("早安", False),  # "早" might match "早上"? Let's check regex for "早上"
    ("早上好", True),
    ("下午茶", True),
    ("去台北", True), # "去" is in keywords
    ("哈哈哈哈", False),
    ("測試", False),
    ("10點", True),
]

print("--- Testing Validator ---")
for msg, expected in test_cases:
    result = validate_schedule_message(msg)
    status = "PASS" if result == expected else "FAIL"
    print(f"[{status}] '{msg}': {result} (Expected: {expected})")
