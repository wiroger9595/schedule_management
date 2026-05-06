# 變更總結 (2026-04-30)

## 修復的 Bug

### 1. 過去行程編輯流程 (schedules.py)
**問題**: 當用戶修改過去的行程時，系統只顯示「確認嗎？」但沒有讓用戶輸入新時間。

**根本原因**:
- Auto-confirm 邏輯過度激進，直接跳過 AI graph，導致新輸入被忽略
- 新時間也在過去時（AI 保留原始日期），系統仍然只問「確認」而不問「要改到什麼時候」

**修復**:
1. **改進 auto-confirm 流程** (line 833-850)
   - 移除自動設定 `confirm_past_edit=True` 的行為
   - 改為 run graph 來處理用戶新輸入
   - 在 DB 層跳過過去行程檢查（用戶已確認）

2. **新增「新時間也在過去」的偵測** (line 1358-1396)
   - 檢查更新後的 `start_time` 是否仍在過去
   - 如果在過去 → 詢問「想改到什麼時候」而不是「確認嗎」
   - 保留 `_pending_edit_schedule_id` 供下一輪 AI 處理

3. **保留 context 在 follow-up 時** (line 948-954)
   - 當用戶在警告後輸入新訊息但 AI 還需更多資訊
   - 保留 `_pending_past_edit_id` 在返回的 data 中

### 2. 移除 Cerebras thinking_budget_tokens 配置 (ai_service.py)
**問題**: Cerebras API 不支持 `thinking_budget_tokens` 參數，導致錯誤。

**修復**: 移除第 421-423 行的 `thinking_budget_tokens` 設定，改用預設配置。

---

## 新增功能

### 模型對比診斷工具

#### 新檔案:
- `server/app/api/endpoints/debug.py` - 新 endpoint 與質量評分邏輯
- `DEBUG_API_USAGE.md` - 完整使用文檔和範例
- `test_debug_api.py` - 測試腳本

#### 功能:
**Endpoint**: `POST /debug/compare-models`

同時呼叫**所有可用的 AI model**（Cerebras/Qwen、Groq、Gemini）對同一個提示進行回應，對比質量：

```json
{
  "user_message": "明天下午三點跟小明在信義區吃飯",
  "schedule_list": [...],
  "conversation_history": [],
  "current_data": {},
  "memory_snippets": [],
  "contact_hints": []
}
```

**回應範例**:
```json
{
  "user_message": "明天下午三點跟小明在信義區吃飯",
  "results": {
    "Cerebras/qwen-3-235b": {
      "intent": "create",
      "is_complete": true,
      "quality_score": 90,
      "quality_notes": ["✓ 決定完整", "✓ Intent: create", "✓ 有回覆訊息"]
    },
    "Groq/llama-3.3-70b": {
      "intent": "create",
      "is_complete": false,
      "quality_score": 75,
      "quality_notes": ["✓ Intent: create", "⊘ 需要更多資訊"]
    },
    "Gemini/gemini-2.0-flash": {
      "error": "rate_limited",
      "quality_score": 0
    }
  },
  "consensus": {
    "total_models": 3,
    "successful_models": 2,
    "overall_agreement": 0.67,
    "most_common_intent": "create"
  },
  "best_model": "Cerebras/qwen-3-235b"
}
```

#### 質量評分標準:
- **決定完整** (+30 pts): `is_complete=true`
- **正確 Intent** (+20 pts): create/edit/delete/query 之一
- **正確 schedule_id** (+25 pts): edit 時 ID 必須在清單中
- **合理資料** (+15 pts): 有意義欄位 + 正確日期格式
- **有回覆訊息** (+10 pts): 非空 AI 回覆

扣分項:
- **無效 schedule_id** (-20 pts)
- **完成但資料不足** (-15 pts)

#### 使用場景:
1. **驗證新 prompt** - 修改後對所有 model 測試
2. **選最佳 model** - 根據分數決定預設
3. **偵測不一致** - 找出 model 分歧的原因
4. **優化約束** - 根據失敗案例改進 prompt

---

## 修改的檔案

### `server/app/api/endpoints/schedules.py`
- Line 833-850: 重新設計 auto-confirm 邏輯
- Line 948-954: 保留 context 在 follow-up 時  
- Line 1358-1396: 新增「新時間也在過去」的檢查與提示

### `server/app/services/ai_service.py`
- Line 421-423: 移除 `thinking_budget_tokens` 設定
- Line 430-448: 移除 `_extra_body` 參數
- Line 712-760: 新增 `process_conversation_with_provider()` 方法

### `server/app/api/api.py`
- Line 10: 導入 debug router
- Line 20: 註冊 debug endpoint

---

## 測試結果

```
🔍 Testing all 3 models...
📝 Input: 明天下午三點跟小明在信義區吃飯

✓ Cerebras/qwen-3-235b
  Intent: create (✓ 完整, 質量分數: 90)
  結果: 直接建立行程

✓ Groq/llama-3.3-70b
  Intent: create (⊘ 需問結束時間, 質量分數: 75)
  結果: 詢問幾點結束

✓ Gemini/gemini-2.0-flash
  結果: 被速率限制（正常）

📊 Summary: 2/3 successful, overall agreement: 67%
🎯 Best model: Cerebras/qwen-3-235b
```

---

## 下一步建議

### 優先高:
1. **使用新診斷工具** - 定期用 `/debug/compare-models` 驗證 prompt 品質
2. **記錄失敗案例** - 當某個 model 失敗時，用失敗訊息優化 constraint_store
3. **監控 Gemini 限速** - 考慮調整 Gemini 的權重或 fallback 時機

### 優先中:
1. 新增 UI 面板顯示診斷結果（便於非技術人員檢視）
2. 自動每日運行測試用例並記錄趨勢
3. 在 constraint_store 中記錄每個 model 的常見錯誤

### 優先低:
1. 支援選擇特定 model 進行測試（`?models=cerebras,groq`）
2. 導出診斷報告為 CSV/JSON
3. 建立 model 性能儀表板

---

## 如何驗證修復

### 過去行程編輯流程:
```bash
# 建立過去行程後，測試修改
# 1. 新時間也在過去 → 應該問「改到什麼時候」
# 2. 新時間在未來 → 應該問「確認嗎」
# 3. 用戶回覆新時間 → 應該處理並更新（不會被忽略）
```

### 模型對比:
```bash
python test_debug_api.py
# 或
curl -X POST http://localhost:8000/debug/compare-models \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_message": "..."}' 
```

---

## 相關文檔
- `DEBUG_API_USAGE.md` - 詳細使用指南和 API 文檔
- `test_debug_api.py` - 獨立測試腳本
- `server/CLAUDE.md` - Backend 約定
- `mobile/CLAUDE.md` - Mobile 約定
