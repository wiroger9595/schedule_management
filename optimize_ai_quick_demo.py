#!/usr/bin/env python3
"""
Quick demo of the AI optimization test suite (tests Groq only for speed)
"""
import sys
sys.path.insert(0, "server")

from optimize_ai_assistant import AIAssistantTester

# Quick demo - test only Cerebras (index 0) for speed
tester = AIAssistantTester()

print("🚀 Quick Demo: Testing Cerebras Model Only\n")
print(f"Total test cases: {len(tester.test_cases)}\n")

# Show first few test cases
print("Sample Test Cases:")
for i, tc in enumerate(tester.test_cases[:5]):
    print(f"  {i+1}. [{tc.category}] {tc.name}")
    print(f"     Input: {tc.user_message}")
    print(f"     Expected: intent={tc.expected_intent}, complete={tc.expected_complete}\n")

# Run tests on Cerebras only (index 0)
print("\nRunning tests on Cerebras/qwen-3-235b...")
print("="*80)

results = tester.run_tests(models_to_test=[0])

# Print summary
print("\n" + "="*80)
tester.print_summary()

# Generate report
tester.generate_report("ai_test_report_quick.html")
print("\n✅ Report generated: ai_test_report_quick.html")

# Show recommendations
print("\n💡 AI Optimization Recommendations:")
recommendations = tester._generate_recommendations()
for i, rec in enumerate(recommendations, 1):
    print(f"\n{i}. {rec['title']}")
    print(f"   {rec['description']}")
    print(f"   Priority: {rec['priority']}")
