#!/usr/bin/env python3
import sys
sys.path.insert(0, "server")

from optimize_ai_assistant import AIAssistantTester, TestCase
from app.services.ai_service import ai_service

tester = AIAssistantTester()

# Test with Cerebras only
print("🔍 Analyzing failures with Cerebras model\n")
results = tester.run_tests(models_to_test=[0])

# Group failures by category
failures_by_category = {}
for model, test_results in results.items():
    for result in test_results:
        if not result.passed:
            cat = result.test_case.category
            if cat not in failures_by_category:
                failures_by_category[cat] = []
            failures_by_category[cat].append((result.test_case.id, result.test_case.name, result.errors))

# Print organized failures
for category in sorted(failures_by_category.keys()):
    failures = failures_by_category[category]
    print(f"\n📌 {category.upper()} ({len(failures)} failures)")
    for test_id, test_name, errors in failures:
        print(f"  • {test_id} - {test_name}")
        for error in errors:
            print(f"    - {error}")
