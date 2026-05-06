# AI 行程助理優化指南

## 📋 功能概述

`optimize_ai_assistant.py` 是一個**全面的測試框架**，用來：
- ✅ 評估 AI 行程助理在 25+ 個真實場景中的表現
- 📊 對比多個 AI 模型的質量
- 🔍 找出薄弱環節和改進方向
- 📈 生成詳細的 HTML 分析報告

## 🚀 快速開始

### 方式 1: 快速演示（推薦首次使用）
```bash
python optimize_ai_quick_demo.py
```
- 只測試 Groq 模型（速度快，~1 分鐘）
- 生成 `ai_test_report_quick.html`

### 方式 2: 完整測試（所有模型）
```bash
python optimize_ai_assistant.py
```
- 測試所有可用模型：Cerebras、Groq、Gemini
- 生成 `ai_test_report.html`
- 耗時：3-5 分鐘

### 方式 3: 指定模型
```bash
# 只測試 Cerebras (index 0)
python optimize_ai_assistant.py --models 0

# 測試 Cerebras 和 Groq
python optimize_ai_assistant.py --models 0 1

# 指定輸出文件
python optimize_ai_assistant.py --report custom_report.html
```

## 📊 測試用例分類

### 1. Parsing (時間、日期、地點解析)
```
✓ 相對日期: 明天、後天、下禮拜五
✓ 時間段: 上午、下午、晚上
✓ 地點識別: 具體地點、品牌店鋪、線上會議
```

### 2. Intent Detection (意圖辨識)
```
✓ 建立行程: 「安排...」「幫我...」
✓ 編輯行程: 「改...」「把...改成...」
✓ 刪除行程: 「刪除...」「取消...」
✓ 查詢行程: 「我有什麼...」「列出...」
```

### 3. Location Handling (地點處理)
```
✓ 明確地點: 信義星巴克、台北101
✓ 模糊地點: 星巴克（缺分店）
✓ 線上會議: 不需要物理地點
```

### 4. Past Schedules (過去行程)
```
✓ 保留日期修改: 把 3/15 的會改成 8pm
✓ 改到未來: 把 3/15 的會改到下禮拜五
✓ 同時改多個字段
```

### 5. Participants (參與者處理)
```
✓ 單一參與者: 跟小明...
✓ 多個參與者: 和小明、小美、Robert...
✓ 移除參與者: 把 X 從會議中移除
✓ 同名聯絡人: 應該要求澄清
```

### 6. Edge Cases (邊界情況)
```
✓ 模糊指代: 「改一下那個」
✓ 同名聯絡人: 有多個 「小明」
✓ 缺少關鍵信息: 逐步詢問
✓ 離題問題: 拒絕並引導
```

## 📈 理解報告

### 整體概況表
| 欄位 | 含義 |
|------|------|
| 通過率 | 測試通過的百分比（期望 > 80%） |
| 平均分數 | 測試的平均質量分數（0-100） |
| 平均時間 | 平均回應時間（毫秒） |

### 質量分數計算

```
基礎分: 50
+ 意圖正確: +25 分
+ 完整性正確: +15 分
+ 有回覆訊息: +10 分
+ 合理資料格式: 額外獎勵

總分: 0-100
```

### 分數解釋
- **80-100**: ✅ 優秀，無需改進
- **60-79**: ⚠️ 可接受，有改進空間
- **< 60**: ❌ 需要改進

## 🔍 常見問題分析

### 意圖辨識失敗
**症狀**: `intent_mismatch: expected create, got edit`

**原因分析**:
- Prompt 中的意圖檢測規則不清楚
- 模型無法區分「建立」vs「編輯」的語境

**修復方案**:
1. 查看 `prompt_builder.py` 的 system prompt
2. 在 "工具選擇規則" 部分加入更多例子
3. 重新運行測試驗證改進

### 完整性判斷錯誤
**症狀**: `completeness_mismatch: expected True, got False`

**原因分析**:
- 模型認為缺少必要字段（如地點、時間）
- 用戶輸入不完整但 AI 應該能推斷

**修復方案**:
1. 檢查測試用例是否合理
2. 在 `constraint_store` 記錄失敗案例
3. 優化 prompt 中的「推斷規則」

### 回應時間慢
**症狀**: 平均時間 > 5000ms

**原因分析**:
- 模型冷啟動或 API 延遲
- 地點驗證邏輯耗時

**修復方案**:
1. 調整 `ai_service.py` 中的超時
2. 考慮降低該模型的優先度
3. 檢查 HERE API 性能

## 💡 優化工作流

### Step 1: 執行測試
```bash
python optimize_ai_assistant.py
```

### Step 2: 分析報告
- 開啟 `ai_test_report.html`
- 查看 "按類別分析" 找出弱項
- 記下失敗的測試案例

### Step 3: 定位問題
```bash
# 找出失敗案例的詳細信息
grep "✗" ai_test_report.html  # 查看失敗項

# 查看模型錯誤模式
# 例如: 所有 "past_schedule" 類的測試都失敗?
#      所有模型都在 "location_2" 失敗?
```

### Step 4: 修復 Prompt
基於失敗類型修改相應部分：

**如果時間解析失敗**:
```python
# 編輯 prompt_builder.py 的時間規則部分
def build_system_prompt(...):
    # 在「時間規則」部分添加更多例子
```

**如果地點識別失敗**:
```python
# 編輯 prompt_builder.py 的地點規則部分
# 或優化 here_service.py 的搜尋邏輯
```

**如果參與者識別失敗**:
```python
# 檢查 contact_hints 是否正確傳入
# 優化 "參與者命名規則" 中的 @ 符號處理
```

### Step 5: 重新測試
```bash
python optimize_ai_assistant.py
```

比較新舊報告，驗證改進。

## 📊 報告查看

生成的 HTML 報告包含：

1. **整體概況** - 所有模型的通過率、分數、響應時間
2. **按類別分析** - 6 大類別的表現 + 常見問題
3. **詳細測試結果** - 每個測試的完整信息
4. **優化建議** - 自動生成的改進方案

### 在本地查看
```bash
# Mac/Linux
open ai_test_report.html

# 或用任何瀏覽器開啟
```

## 🔧 進階用法

### 新增自定義測試用例
```python
from optimize_ai_assistant import TestCase, AIAssistantTester

tester = AIAssistantTester()

# 新增測試用例
tester.test_cases.append(TestCase(
    id="custom_1",
    name="我的自定義場景",
    user_message="明天和我的團隊開會討論新功能",
    category="participants",
    expected_intent="create",
    expected_complete=False,
))

# 運行
results = tester.run_tests()
```

### 整合到 CI/CD
```bash
#!/bin/bash
# 每日自動運行測試
python optimize_ai_assistant.py --report reports/$(date +%Y-%m-%d).html

# 檢查是否通過
if grep -q "失敗率" reports/$(date +%Y-%m-%d).html; then
    echo "Alert: AI quality degraded"
    # 發送告警郵件
fi
```

### 批量測試不同 Prompt
```python
# 在 prompt_builder.py 中準備多個 prompt 版本
# 分別測試每個版本

for version in ["v1", "v2", "v3"]:
    print(f"\nTesting prompt {version}...")
    # 切換 prompt
    # 運行測試
    # 比較結果
```

## 📈 長期監控

### 建立基準線
第一次運行測試時，保存報告作為基準：
```bash
python optimize_ai_assistant.py --report baseline_report.html
```

### 定期測試
```bash
# 每週運行一次
# 保存到帶日期的文件
```

### 對比分析
```bash
# 使用 diff 工具對比報告
# 或寫指令碼提取分數變化
```

## 🎯 優化目標

### 理想狀態
```
✅ 通過率: 90%+
✅ 平均分數: 85+
✅ 平均時間: < 2000ms
✅ 各類別通過率: 80%+
```

### 可接受狀態
```
✅ 通過率: 75%+
✅ 平均分數: 70+
✅ 平均時間: < 3000ms
✅ 關鍵類別（parsing, intent）: 85%+
```

## 🆘 故障排除

### 測試超時
```bash
# 可能是模型 API 慢
# 解決方案:
# 1. 檢查網路連接
# 2. 減少測試用例數量
# 3. 只測試快速的模型
python optimize_ai_assistant.py --models 1
```

### API Key 錯誤
```bash
# 確保環境變數設定正確
echo $CEREBRAS_API_KEY
echo $GROQ_API_KEY
echo $GEMINI_API_KEY
```

### 模型不可用
```bash
# 檢查 ai_service.py 中的 providers 配置
# 確保至少有一個 API key 有效
```

## 📞 支援

遇到問題？檢查：
1. 是否有足夠的 API quota
2. 網路連接是否正常
3. 環境變數是否設定
4. 測試用例描述是否清楚

---

## 範例工作流

```bash
# 1. 執行快速演示
python optimize_ai_quick_demo.py

# 2. 開啟報告查看結果
open ai_test_report_quick.html

# 3. 發現「past_schedule」通過率低

# 4. 編輯 prompt_builder.py，加強過去行程規則

# 5. 再次運行完整測試
python optimize_ai_assistant.py

# 6. 對比報告，確認改進
```

祝你優化順利！🎯
