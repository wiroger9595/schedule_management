# AI 行程助理測試 & 優化框架完全指南

## 📦 已建立的工具套件

### 1️⃣ 模型對比診斷工具
**檔案**: `server/app/api/endpoints/debug.py`

**功能**: 同時呼叫所有 AI 模型，對比回答質量
```bash
# API 端點
POST /debug/compare-models

# 輸入
{
  "user_message": "明天下午三點跟小明在信義區吃飯",
  "schedule_list": [...],
  "contact_hints": [...],
  ...
}

# 輸出
{
  "results": {
    "Cerebras/qwen-3-235b": { "quality_score": 90 },
    "Groq/llama-3.3-70b": { "quality_score": 75 },
    "Gemini/gemini-2.0-flash": { "quality_score": 60 }
  },
  "best_model": "Cerebras/qwen-3-235b",
  "consensus": { "overall_agreement": 0.67 }
}
```

**適用場景**:
- ✅ 快速驗證新 prompt 是否改善
- ✅ 找出最佳模型作為預設
- ✅ 識別模型分歧
- ✅ 調試特定輸入

**相關文件**: `DEBUG_API_USAGE.md`, `test_debug_api.py`

---

### 2️⃣ 全面測試框架
**檔案**: `optimize_ai_assistant.py`

**25+ 個測試用例**，涵蓋：
- 時間解析（相對日期、時間段等）
- 意圖辨識（create/edit/delete/query）
- 地點處理（明確、模糊、線上）
- 過去行程編輯
- 參與者識別（單一、多人、同名）
- 邊界情況（模糊指代、缺信息等）

**執行**:
```bash
# 快速演示（只測 Groq）
python optimize_ai_quick_demo.py

# 完整測試（所有模型）
python optimize_ai_assistant.py

# 指定模型
python optimize_ai_assistant.py --models 0 1
```

**輸出**:
- 📊 HTML 報告（詳細分析 + 建議）
- 📈 按類別分析
- 💡 自動優化建議

**相關文件**: `OPTIMIZE_AI_GUIDE.md`

---

### 3️⃣ 快速演示腳本
**檔案**: `optimize_ai_quick_demo.py`

輕量版本，只測 Groq，~1 分鐘完成
```bash
python optimize_ai_quick_demo.py
```

---

### 4️⃣ 獨立測試工具
**檔案**: `test_debug_api.py`

不需要 API 端點，直接測試 AI service
```bash
python test_debug_api.py
```

---

## 📊 測試流程概覽

```
User Input
   ↓
優化測試框架
   ├─ 時間解析 (4 個用例)
   ├─ 意圖辨識 (4 個用例)
   ├─ 地點處理 (3 個用例)
   ├─ 過去行程 (2 個用例)
   ├─ 參與者識別 (3 個用例)
   └─ 邊界情況 (4 個用例)
   ↓
質量評分 (0-100)
   ├─ 意圖正確 (+25)
   ├─ 完整性 (+15)
   ├─ 回覆訊息 (+10)
   └─ 資料合理 (+15)
   ↓
HTML 報告 + 建議
```

---

## 🎯 使用場景

### 場景 1: 修改 Prompt 後驗證
```bash
# 修改 prompt_builder.py

# 快速驗證
python optimize_ai_quick_demo.py
# 查看 ai_test_report_quick.html

# 好的話再做完整測試
python optimize_ai_assistant.py
```

### 場景 2: 選擇最佳模型
```bash
# 執行完整測試
python optimize_ai_assistant.py

# 查看報告中的 "best_model"
# 更新 ai_service.py 的優先度
```

### 場景 3: 除錯特定問題
```bash
# 使用 API 診斷工具
curl -X POST http://localhost:8000/debug/compare-models \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "明天改成晚上七點",
    "schedule_list": [...]
  }'
```

### 場景 4: 持續監控
```bash
# 設定每日自動測試
0 2 * * * cd /path && python optimize_ai_assistant.py \
  --report reports/$(date +\%Y-\%m-\%d).html
```

---

## 🔄 改進迴圈

### 第 1 週: 建立基準
```bash
python optimize_ai_assistant.py --report baseline.html
```
記錄基線通過率、分數、時間。

### 第 2-4 週: 重點改進
1. 確定通過率最低的類別
2. 編輯相應的 prompt 部分
3. 執行測試驗證改進
4. 迭代直到該類別 > 85%

### 第 5 週: 驗證不退化
```bash
python optimize_ai_assistant.py
# 確保總體通過率 ↑
# 各類別都沒有 ↓
```

---

## 📈 性能目標

| 指標 | 目標 | 現況 |
|------|------|------|
| 總通過率 | 85%+ | TBD |
| 平均分數 | 75+ | TBD |
| 平均響應時間 | < 2s | TBD |
| Parsing 類別 | 90%+ | TBD |
| Intent 類別 | 90%+ | TBD |
| Past Schedule | 85%+ | TBD |

---

## 🔧 實現細節

### 新增的 API 端點
```python
# server/app/api/endpoints/debug.py
@router.post("/debug/compare-models")
def compare_ai_models(request: dict)
```

### 新增的方法
```python
# server/app/services/ai_service.py
def process_conversation_with_provider(
    provider_index: int,
    user_message: str,
    ...
)
```

### Bug 修復
✅ 過去行程編輯流程（auto-confirm 跳過 graph）
✅ 新時間也在過去的偵測和提示
✅ Cerebras API 相容性（移除 thinking_budget_tokens）

---

## 📚 文檔對應表

| 工具 | 功能 | 使用指南 | 快速開始 |
|------|------|--------|---------|
| 模型對比診斷 | 對比多個模型 | DEBUG_API_USAGE.md | `test_debug_api.py` |
| 全面測試框架 | 25+ 個測試用例 | OPTIMIZE_AI_GUIDE.md | `python optimize_ai_quick_demo.py` |
| API 端點 | `/debug/compare-models` | DEBUG_API_USAGE.md | curl 範例 |

---

## 🚀 建議的執行順序

### 第一次使用
```bash
# 1. 快速了解框架
python optimize_ai_quick_demo.py

# 2. 查看報告
open ai_test_report_quick.html

# 3. 詳讀優化指南
cat OPTIMIZE_AI_GUIDE.md

# 4. 執行完整測試
python optimize_ai_assistant.py
```

### 日常使用
```bash
# 修改 prompt 後驗證
python optimize_ai_quick_demo.py

# 週末完整驗證
python optimize_ai_assistant.py

# 月末對比趨勢
diff reports/2026-04-15.html reports/2026-05-15.html
```

---

## 💡 優化建議（基於框架分析）

優化框架會自動分析以下方面：

1. **整體識別率** - 是否 > 80%
2. **類別性能** - 找出弱項
3. **模型差異** - 哪個模型最好
4. **性能問題** - 響應時間是否可接受
5. **常見錯誤** - 哪些類型的錯誤頻繁出現

---

## 🔗 集成點

### 與現有系統的集成
```
prompt_builder.py ← 優化框架測試 ← 生成報告
↓
ai_service.py
↓
constraint_store.py ← 記錄失敗案例
↓
schedules.py API
```

### 自動化集成
```bash
# 在 CI/CD 中添加
- name: Run AI Optimization Tests
  run: python optimize_ai_assistant.py --report reports/test-${{ github.run_id }}.html
  
- name: Upload Report
  uses: actions/upload-artifact@v2
  with:
    name: ai-test-reports
    path: reports/
```

---

## 📖 相關文檔

1. **新建**:
   - `OPTIMIZE_AI_GUIDE.md` - 詳細使用指南
   - `DEBUG_API_USAGE.md` - API 文檔
   - `CHANGES_SUMMARY.md` - 修改總結
   - 本文件 - 完整指南

2. **現有**:
   - `server/CLAUDE.md` - Backend 約定
   - `mobile/CLAUDE.md` - Mobile 約定

---

## ✅ 快速檢查清單

- [ ] 閱讀本文件
- [ ] 執行 `python optimize_ai_quick_demo.py`
- [ ] 檢視生成的 HTML 報告
- [ ] 閱讀 `OPTIMIZE_AI_GUIDE.md` 的「理解報告」部分
- [ ] 執行 `python optimize_ai_assistant.py` 進行完整測試
- [ ] 基於報告中的建議進行首次優化
- [ ] 驗證改進效果
- [ ] 建立自動化每週測試

---

## 🎓 進階主題

### 自定義測試用例
修改 `optimize_ai_assistant.py` 中的 `_build_test_cases()` 方法添加特定於你的應用的測試。

### 持續優化
建立一個每週運行的 cron 任務，收集性能數據，識別長期趨勢。

### A/B 測試 Prompts
為多個 prompt 版本生成報告，對比質量指標。

---

祝你優化 AI 行程助理順利！🚀

有任何問題，參考各自的詳細文檔或在代碼中添加 print 語句進行調試。
