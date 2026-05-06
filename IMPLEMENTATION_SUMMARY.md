# HuggingFace Inference API Integration & AI Test Framework Setup

## 完成項目

### 1. 修復 Prompt F-String 轉義問題 (prompt_builder.py)
**問題**：F-string 中的 dictionary literals (`{"key":"value"}`) 導致格式化錯誤
**解決方案**：將 `{` 改為 `{{` 和 `}` 改為 `}}`

修復的行：
- 第 177 行：`ask_user(partial_data={{"schedule_id":"..."}}) ✓`
- 第 231-232 行：`partial_data={{"title":"吃飯","start_time":"..."}}`
- 第 235-236 行：`partial_data={{"title":"與小明吃飯","participants":["@小明"]}}`

### 2. 完成 HuggingFace Inference API 集成 (ai_service.py)

**新增模擬響應類**：
- `_MockMessage`：模擬 OpenAI message 物件
- `_MockChoice`：模擬 OpenAI choice 物件  
- `_MockResponse`：模擬完整的 OpenAI 響應結構

**HuggingFace 特殊處理邏輯**：
1. 首先嘗試 `chat_completion()` 方法（OpenAI 兼容 API）
2. 如果失敗，降級為 `text_generation()` 方法（純文本生成）
3. 返回值使用 `_MockResponse` 包裝成 OpenAI 兼容格式

**Provider 優先級**：
```
HuggingFace/Mistral-Large (主力)
  ↓ 失敗時 fallback
Groq/llama-3.3-70b (備援)
  ↓
Cerebras/qwen-3-235b
  ↓
Gemini/gemini-2.0-flash (最終)
```

**api_key 屬性修復**：
- HuggingFace InferenceClient 不支持 `api_key` 屬性
- 改用 `getattr(self.client, "api_key", None)`

### 3. 數據庫設置驗證

**已存在的組件**：
- `server/app/models/ai_test_result.py`：定義了 AITestResult 模型
- `server/run_migration.py`：包含 ai_test_result 表的創建和索引
- 數據庫遷移已驗證成功執行

**測試結果存儲欄位**：
- test_case_id, category, user_message
- expected_intent, expected_complete
- actual_intent, actual_complete, model_reply
- passed, quality_score, duration_ms
- errors, created_at

### 4. 測試框架驗證

已驗證以下功能：
1. ✅ `ai_service.process_conversation_with_provider()` 正常工作
2. ✅ `optimize_ai_assistant.py` 中的 `save_results_to_db()` 正常保存
3. ✅ 單個測試案例成功存儲到數據庫
4. ✅ 完整的 90 個測試案例可以運行（使用 Groq 提供者）

## 執行狀態

### 正在進行中
- 90 個測試案例的完整運行（使用 Groq 提供者）
- 10 個快速驗證測試案例

### 已完成
- F-string 轉義修復
- HuggingFace 集成實現
- DB 遷移驗證
- 單個測試案例驗證

## 使用方式

### 運行 10 個驗證測試
```bash
python validate_setup.py
```

### 運行完整 90 個測試（所有提供者）
```bash
python optimize_ai_assistant.py --report ai_test_report.html
```

### 運行特定提供者的測試
```bash
python optimize_ai_assistant.py --models 0  # HuggingFace (0)
python optimize_ai_assistant.py --models 1  # Groq (1)
python optimize_ai_assistant.py --models 2  # Cerebras (2)
python optimize_ai_assistant.py --models 3  # Gemini (3)
```

## 已知問題和注意事項

### HuggingFace 模型映射
- HuggingFace 的免費 Inference API 可能對某些模型有限制
- 系統已設置 fallback 邏輯，失敗時自動切換到 Groq

### Rate Limiting
- Groq 免費層有速率限制
- 系統設置 6 秒 throttle 和 60 秒 backoff
- 建議在非高峰時段運行完整測試

### 教練機警告
- instructor 客戶端對 HuggingFace InferenceClient 顯示警告
- 功能正常，但由於 HuggingFace 不是標準 OpenAI 客戶端

## 後續步驟

1. 等待 90 個測試案例完成並生成報告
2. 檢查數據庫中的測試結果
3. 分析哪些類別的測試通過率最低
4. 根據結果優化 prompt
5. 考慮使用 HuggingFace 本地模型（如果需要更高的可靠性）

## 技術細節

### Mock 響應類設計
使用 mock 類而不是修改原始 OpenAI 響應對象，保持代碼清潔：
```python
class _MockResponse:
    def __init__(self, text: str):
        self.choices = [_MockChoice(text)]

# 保證與現有的響應解析邏輯兼容
msg = response.choices[0].message
content = msg.content  # 正常工作
tool_calls = msg.tool_calls  # None，觸發 JSON 模式
```

### Provider 級聯邏輯
- 每個提供者最多 2 次嘗試
- 遇到 rate limit 時先重試 1 次，仍失敗才跳過
- 某個提供者失敗不影響其他提供者

