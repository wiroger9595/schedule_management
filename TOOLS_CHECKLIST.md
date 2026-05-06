# 🛠️ AI 行程助理優化工具清單

## 已建立的工具和文檔

### 🧪 測試工具

| 工具 | 檔案 | 用途 | 執行 |
|------|------|------|------|
| **快速演示** | `optimize_ai_quick_demo.py` | 30 秒快速測試 | `python optimize_ai_quick_demo.py` |
| **完整測試框架** | `optimize_ai_assistant.py` | 25+ 用例全面測試 | `python optimize_ai_assistant.py` |
| **獨立測試** | `test_debug_api.py` | 不需 API 端點測試 | `python test_debug_api.py` |
| **API 診斷** | `/debug/compare-models` | 運行中對比模型 | 見下方 API 部分 |

### 📖 文檔

| 文檔 | 內容 | 適合讀者 |
|------|------|---------|
| `OPTIMIZE_AI_GUIDE.md` | 詳細使用手冊 | 使用測試框架的人 |
| `DEBUG_API_USAGE.md` | API 使用指南 | 開發者、系統整合 |
| `TEST_FRAMEWORK_SUMMARY.md` | 本文件 - 完整指南 | 系統管理者 |
| `CHANGES_SUMMARY.md` | 所有修改總結 | 想瞭解改動的人 |

### 🔧 Bug 修復

| Bug | 檔案 | 修復內容 |
|-----|------|---------|
| 過去行程編輯 | `schedules.py` | 修復 auto-confirm 跳過 graph 的問題 |
| 過去時間提示 | `schedules.py` | 新增「新時間也在過去」的檢查 |
| Cerebras API | `ai_service.py` | 移除不支持的 `thinking_budget_tokens` 參數 |

### 🚀 API 端點

```
POST /debug/compare-models

功能: 同時呼叫所有 AI 模型並對比質量
輸入: user_message, schedule_list, contact_hints 等
輸出: 所有模型的回答 + 質量評分 + 最佳模型建議
```

---

## 📊 功能矩陣

### 測試工具覆蓋範圍

| 功能 | 快速演示 | 完整框架 | API 診斷 |
|------|--------|--------|---------|
| 時間解析 | ✅ | ✅ | ✅ |
| 意圖辨識 | ✅ | ✅ | ✅ |
| 地點處理 | ✅ | ✅ | ✅ |
| 過去行程 | ✅ | ✅ | ✅ |
| 參與者識別 | ✅ | ✅ | ✅ |
| 邊界情況 | ⭕ | ✅ | ✅ |
| 多模型對比 | ✅ | ✅ | ✅ |
| 質量評分 | ✅ | ✅ | ✅ |
| HTML 報告 | ✅ | ✅ | - |
| 自動建議 | ⭕ | ✅ | - |

✅ = 完整支持  
⭕ = 基礎支持  
\- = 不支持

---

## 🎯 使用場景速查表

### 我想要... → 使用這個工具

| 需求 | 工具 | 命令 |
|------|------|------|
| 快速驗證改動有沒有帮助 | 快速演示 | `python optimize_ai_quick_demo.py` |
| 全面評估 AI 質量 | 完整測試 | `python optimize_ai_assistant.py` |
| 除錯特定輸入 | API 診斷 | `curl ... /debug/compare-models` |
| 對比模型性能 | 完整測試或 API | 見上方 |
| 選擇最佳模型 | 完整測試 | 查看報告中 `best_model` |
| 監控長期趨勢 | 完整測試 | 定期執行並比較報告 |

---

## 📋 工作流指南

### 情境 1: 第一次使用
```
1. python optimize_ai_quick_demo.py
   ↓
2. 開啟 ai_test_report_quick.html
   ↓
3. 閱讀 OPTIMIZE_AI_GUIDE.md
   ↓
4. python optimize_ai_assistant.py
```

### 情境 2: 修改 Prompt 後驗證
```
1. 編輯 prompt_builder.py
   ↓
2. python optimize_ai_quick_demo.py （快速驗證）
   ↓
3. 查看報告，評估改動
   ↓
4. python optimize_ai_assistant.py （完整驗證）
   ↓
5. 對比改動前後的報告
```

### 情境 3: 持續優化迴圈
```
第 1 週: python optimize_ai_assistant.py → 建立基準 (baseline.html)
↓
第 2-4 週:
  - 找出最低分類別
  - 優化相應 prompt 部分
  - 快速驗證 (optimize_ai_quick_demo.py)
  - 迭代
↓
第 5 週: python optimize_ai_assistant.py → 對比 baseline.html
```

---

## 🔍 質量指標

### 測試框架提供的指標

1. **通過率** - 測試通過的百分比 (目標: 85%+)
2. **平均分數** - 0-100 的質量評分 (目標: 75+)
3. **平均時間** - 平均回應時間毫秒 (目標: < 2000ms)
4. **類別分析** - 各類別的通過率 (目標: 80%+ 每個類別)
5. **模型對比** - 各模型的相對性能
6. **共識度** - 多個模型的意見一致程度

### 報告中的關鍵數字

```
總體通過率: 82/100 (82%)     ← 目標 85%+
平均分數: 76.3/100           ← 目標 75+
平均時間: 1854ms             ← 目標 < 2000ms

按類別:
  Parsing: 85%   ✅ 好
  Intent: 90%    ✅ 優秀
  Location: 75%  ⚠️ 可接受
  Past: 70%      ❌ 需改進
  Participants: 80% ✅ 好
  Edge: 65%      ❌ 需改進

最佳模型: Cerebras/qwen-3-235b (87%)
```

---

## 🔄 測試框架工作原理

```
用戶輸入
   ↓
[測試用例 1-25]
   ├─ 時間解析 (parse_1 ~ 4)
   ├─ 意圖辨識 (intent_1 ~ 4)
   ├─ 地點處理 (location_1 ~ 3)
   ├─ 過去行程 (past_1 ~ 2)
   ├─ 參與者識別 (part_1 ~ 3)
   └─ 邊界情況 (edge_1 ~ 4)
   ↓
AI 模型處理
   ↓
質量評分引擎
   ├─ 意圖匹配 (±25 分)
   ├─ 完整性檢查 (±15 分)
   ├─ 回覆品質 (±10 分)
   └─ 資料合理性 (±15 分)
   ↓
結果收集
   ├─ 個別測試結果
   ├─ 模型對比
   ├─ 類別分析
   └─ 自動建議
   ↓
HTML 報告輸出
```

---

## 📈 改進迴圈

### 典型改進過程

**第 1 次**:
- 執行 `optimize_ai_assistant.py`
- 通過率: 72% (基準)
- 最弱項: `past_schedule` (60%)

**第 2 次** (改進過去行程的 prompt):
- 執行 `optimize_ai_quick_demo.py`
- 過去行程: 60% → 75%
- 通過率: 72% → 77%

**第 3 次** (改進邊界情況):
- 執行 `optimize_ai_quick_demo.py`
- 邊界情況: 65% → 78%
- 通過率: 77% → 81%

**第 4 次** (確認沒有退化):
- 執行 `optimize_ai_assistant.py`
- 通過率: 81% ✓ (超過目標)

---

## 🛡️ 最佳實踐

### DO ✅
- 定期執行測試 (至少每週)
- 修改 prompt 後立即驗證
- 保存歷史報告用於對比
- 逐次改進（一個類別一次）
- 檢查是否有退化 (regression)

### DON'T ❌
- 一次修改多個部分（難以定位改進來源）
- 忽視邊界情況測試
- 只看通過率，忽視平均分數
- 不檢查各模型的差異
- 假設改動一定有幫助（必須驗證）

---

## 🚨 常見問題

### Q: 測試很慢怎麼辦？
A: 用 `optimize_ai_quick_demo.py` (只測 Groq，~30秒)

### Q: 某個模型一直失敗怎麼辦？
A: 檢查 API key、網路、速率限制。或在 `ai_service.py` 中降低其優先度。

### Q: 怎麼知道我的改進有沒有幫助？
A: 對比改動前後的報告。通過率、分數、時間都要對比。

### Q: 可以只測特定類別嗎？
A: 修改 `optimize_ai_assistant.py` 中的 `_build_test_cases()` 並註解掉其他。

### Q: 怎麼加入自己的測試用例？
A: 在 `_build_test_cases()` 中 append 新的 TestCase。

---

## 📞 支援資源

| 遇到的問題 | 查看 |
|-----------|------|
| 怎麼執行測試？ | `OPTIMIZE_AI_GUIDE.md` § 快速開始 |
| 理解報告？ | `OPTIMIZE_AI_GUIDE.md` § 理解報告 |
| 使用 API？ | `DEBUG_API_USAGE.md` |
| 瞭解改動？ | `CHANGES_SUMMARY.md` |
| 架構原理？ | 本文件 |

---

## ✨ 快速參考

### 3 個最常用命令

```bash
# 1. 快速驗證 (最常用)
python optimize_ai_quick_demo.py

# 2. 完整驗證 (週末跑)
python optimize_ai_assistant.py

# 3. API 診斷 (除錯用)
curl -X POST http://localhost:8000/debug/compare-models ...
```

### 3 個關鍵指標

1. **通過率** - 越高越好 (目標 85%+)
2. **平均分數** - 越高越好 (目標 75+)
3. **平均時間** - 越低越好 (目標 < 2s)

### 3 個優化步驟

1. 執行測試 → 找出最弱的類別
2. 編輯 prompt_builder.py 的相應部分
3. 再次執行測試 → 驗證改進

---

## 🎓 進階閱讀

完整指南按深度排序：
1. 本文件 (快速概覽) ← 你在這裡
2. `OPTIMIZE_AI_GUIDE.md` (詳細使用)
3. `optimize_ai_assistant.py` (實現細節)
4. `server/app/services/ai_service.py` (AI 核心)
5. `server/app/services/prompt_builder.py` (提示詞優化)

---

**下一步**: 執行 `python optimize_ai_quick_demo.py` 並開啟報告！🚀
