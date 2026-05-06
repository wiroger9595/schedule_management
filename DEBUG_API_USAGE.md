# 行程規劃 AI 模型對比診斷工具

## 功能
呼叫**所有可用的 AI 模型**（Cerebras/Qwen、Groq、Gemini）進行同一個提示，對比它們的回答質量，找出最佳方案。

## Endpoint
```
POST /debug/compare-models
```

## 請求範例

```bash
curl -X POST http://localhost:8000/debug/compare-models \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "明天下午三點跟小明在信義區吃飯",
    "schedule_list": [
      {
        "schedule_id": "abc-123",
        "title": "跟Robert開會",
        "meeting_start_time": "2026-04-30T10:00:00",
        "meeting_location": "台北101"
      }
    ],
    "conversation_history": [],
    "current_data": {},
    "memory_snippets": [],
    "contact_hints": [
      {
        "nick_name": "小明",
        "similarity": 0.95,
        "phone": "0912345678"
      }
    ]
  }'
```

## 回應範例

```json
{
  "user_message": "明天下午三點跟小明在信義區吃飯",
  "timestamp": "2026-04-30T15:30:45.123456",
  "results": {
    "Cerebras/qwen-3-235b": {
      "model": "qwen-3-235b-a22b-instruct-2507",
      "intent": "create",
      "is_complete": true,
      "reply": "✅ 已為您建立行程！",
      "updated_data": {
        "title": "與小明吃飯",
        "start_time": "2026-05-01T15:00:00",
        "location": "信義區",
        "participants": ["@小明"]
      },
      "missing_fields": [],
      "quality_score": 90,
      "quality_notes": [
        "✓ 決定完整",
        "✓ Intent: create",
        "✓ 合理的資料",
        "✓ 有回覆訊息"
      ]
    },
    "Groq/llama-3.3-70b": {
      "model": "llama-3.3-70b-versatile",
      "intent": "create",
      "is_complete": true,
      "reply": "好的，我為您建立了行程",
      "updated_data": {
        "title": "與小明吃飯",
        "start_time": "2026-05-01T15:00:00",
        "location": "信義區",
        "participants": ["@小明"]
      },
      "quality_score": 85,
      "quality_notes": [
        "✓ 決定完整",
        "✓ Intent: create",
        "✓ 合理的資料"
      ]
    },
    "Gemini/gemini-2.0-flash": {
      "model": "gemini-2.0-flash",
      "intent": "create",
      "is_complete": true,
      "reply": "行程已建立",
      "updated_data": {...},
      "quality_score": 80,
      "quality_notes": [...]
    }
  },
  "consensus": {
    "total_models": 3,
    "successful_models": 3,
    "intent_agreement": 1.0,
    "complete_agreement": 1.0,
    "overall_agreement": 1.0,
    "most_common_intent": "create"
  },
  "best_model": "Cerebras/qwen-3-235b",
  "total_models": 3
}
```

## 質量評分標準

### 基礎評分（100 分制）
- **決定完整** (+30): `is_complete=true`
- **正確的 Intent** (+20): create/edit/delete/query
- **正確的 schedule_id** (+25): 如果是 edit，ID 必須在清單中
- **合理的資料** (+15): 有意義的欄位和正確的日期格式
- **有回覆訊息** (+10): 非空的 AI 回覆

### 扣分項
- **無效的 schedule_id** (-20): edit 時指向不存在的行程
- **完成但資料不足** (-15): `is_complete=true` 但缺少必要欄位

## 使用場景

### 1. 驗證新 Prompt
修改 `prompt_builder.py` 後，用這個工具對比所有模型的效果：
```bash
# 測試相同的訊息，確認所有模型都理解你的新規則
```

### 2. 找出最佳模型
根據質量分數選擇表現最好的模型作為預設：
```python
best_model = response["best_model"]  # e.g. "Cerebras/qwen-3-235b"
```

### 3. 偵測不一致
如果 `consensus.overall_agreement < 0.7`，表示模型意見不統一：
- 可能是 prompt 不夠清楚
- 或者某個模型的能力有限

### 4. 優化約束條件
根據失敗的模型類型記錄錯誤模式到 `constraint_store`，改進 prompt：
```python
if quality_score < 50:
    record_error("model_confusion", example=user_message)
```

## 進階用法

### Python 客戶端
```python
import requests

token = "your_auth_token"
headers = {"Authorization": f"Bearer {token}"}

response = requests.post(
    "http://localhost:8000/debug/compare-models",
    json={
        "user_message": "把A行程改成晚上七點",
        "schedule_list": [...]
    },
    headers=headers
)

result = response.json()

# 找出最好的回答
best = result["best_model"]
best_data = result["results"][best]
print(f"最佳模型: {best} (分數: {best_data['quality_score']})")

# 檢查共識
if result["consensus"]["overall_agreement"] >= 0.8:
    print("模型意見統一 ✓")
else:
    print("模型分歧 ⚠️ - 需要檢查 prompt")
```

### 批量測試
```python
test_cases = [
    "明天下午三點跟小明在信義區吃飯",
    "把那個舊行程改成下午五點",
    "刪除我的每日站會",
]

for msg in test_cases:
    resp = requests.post(
        "http://localhost:8000/debug/compare-models",
        json={"user_message": msg, ...},
        headers=headers
    )
    result = resp.json()
    best_score = result["results"][result["best_model"]]["quality_score"]
    print(f"[{msg}] 最佳分數: {best_score}")
```

## 常見問題

### Q: 為什麼某個模型總是失敗？
A: 檢查該模型的 API key 是否有效，或速率限制。參考 `ai_service.py` 的級聯邏輯。

### Q: 我只想測試某個模型？
A: 暫時在 `ai_service.py` 中註解掉其他 providers。或者未來可以新增 `?models=cerebras,groq` 參數。

### Q: 分數很低代表什麼？
A: 可能是：
- Prompt 不清楚，模型無法理解
- 模型能力有限（如某些小型模型）
- 輸入資料有問題（行程清單、聯絡人等）

### Q: 該怎麼優化？
A: 
1. 查看 `quality_notes` 找出具體問題
2. 修改 `prompt_builder.py` 的 system prompt
3. 在 `constraint_store` 中記錄錯誤模式
4. 重新測試對比結果
