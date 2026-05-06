#!/usr/bin/env python3
"""
Updated score estimation with improved prompt
"""
import sys
sys.path.insert(0, "server")

from optimize_ai_assistant import AIAssistantTester

tester = AIAssistantTester()

print("🎯 AI 行程助理 - 改進後的性能預估\n")
print("=" * 80)
print("改進項目:")
print("  ✅ 完整性判斷規則更清楚（「有參與者=會議」）")
print("  ✅ Intent 識別規則明確（10+ 種關鍵動詞）")
print("  ✅ 必須提供回覆（避免空回覆）")
print("  ✅ 新增 50 個測試情景")
print("=" * 80)
print()

# Group tests by category
categories = {}
for tc in tester.test_cases:
    cat = tc.category
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(tc)

print("📊 改進後的預估\n")

# 改進後的預估值（應該會更高）
improvements_v2 = {
    "parsing": 0.75,      # 42% → 75%（時間解析規則更清楚）
    "intent": 0.68,       # 17% → 68%（Intent 動詞規則明確化）
    "location": 0.72,     # 0% → 72%（個人行程 vs 會議規則）
    "participants": 0.75, # 0% → 75%（核心原則「有參與者=會議」）
    "past_schedule": 0.78,# 0% → 78%（6 個新測試 + 規則清楚）
    "edge_case": 0.64,    # 0% → 64%（必須提供回覆 + 20 個邊界情況）
}

category_scores = {}
for cat in sorted(categories.keys()):
    tests = categories[cat]
    count = len(tests)
    
    estimated_pass_rate = improvements_v2.get(cat, 0.70)
    estimated_score = 50 + (estimated_pass_rate * 40)
    
    category_scores[cat] = {
        "tests": count,
        "estimated_pass_rate": estimated_pass_rate,
        "estimated_score": estimated_score,
    }
    
    # Show progress bar
    bar_length = int(estimated_pass_rate * 20)
    bar = "█" * bar_length + "░" * (20 - bar_length)
    
    print(f"  {cat:15s} │{bar}│ {estimated_pass_rate*100:5.1f}% | {estimated_score:5.1f}/100")

print()

# Calculate overall metrics
total_tests = len(tester.test_cases)
total_pass_rate = sum(s["estimated_pass_rate"] * s["tests"] 
                      for s in category_scores.values()) / total_tests
total_score = sum(s["estimated_score"] * s["tests"] 
                  for s in category_scores.values()) / total_tests

print("=" * 80)
print(f"📊 總體指標:\n")
print(f"   總測試數: {total_tests} 個")
print(f"   通過率:   {total_pass_rate*100:.1f}%")
print(f"   平均分:   {total_score:.1f}/100")
print()

# Status
if total_score >= 80:
    status = "✅ 達成目標！"
    emoji = "🎉"
elif total_score >= 75:
    status = "⚠️  接近目標，差 5 分"
    emoji = "🔄"
else:
    status = "❌ 仍需改進"
    emoji = "💪"

print(f"{emoji} {status}\n")

print("=" * 80)
print("🚀 後續行動")
print("=" * 80)
print("""
1. 等待 API 恢復（Cerebras/Groq/Gemini）
   
2. API 恢復後執行實際測試:
   python optimize_ai_assistant.py
   
3. 根據實際結果調整 (如有不符)
   
4. 目標: 達成 80+ 分 ✅
""")

print("=" * 80)
if total_score >= 80:
    print(f"✨ 預期達成 {total_score:.1f}/100 分！")
else:
    print(f"📈 預期達成 {total_score:.1f}/100 分 (目標 80)")
print("=" * 80)
