# AI 模型「資料驅動化」重構總結

## 為什麼重構

之前 AI 判斷需要的詞句、規則、聯絡人邏輯**全部寫死在程式碼**：
- `semantic_router_service.py` 寫死 35 個 intent 例句
- `prompt_builder.py` 寫死 ~3000 字的 system prompt 規則
- `chat_utils.py` 寫死 30+ 個關鍵字（NON_NAMES, stop_words）

每次新增/修改判斷邏輯，都要改 code → 測試 → 部署。無法 A/B 測試、無法熱更新。

## 重構後的架構

### 三個新的 vector / lookup 表

| 表 | 用途 | 取代什麼 |
|------|------|---------|
| `intent_anchor` | Intent 分類錨點 | `INTENT_EXAMPLES` dict |
| `prompt_rule` | system prompt 規則 | `prompt_builder.py` 寫死的 markdown |
| `lexicon` | 關鍵字字典 | `NON_NAMES`, `stop_words` set |

### 五個新的 embedding API（cascade）

按免費額度從多到少排序，達到上限自動切換：

```
jina (~30M tokens/day) → voyage (~1.6M/day) → cohere (~144K/day)
  → gemini (1500/day) → hf (~24K/day)
```

每個 provider 失敗時：
- Rate limit (402/429) → 5 分鐘 cooldown
- Auth 失敗 (401) → 24 小時跳過
- 其他錯誤 → 1 分鐘 cooldown

## 效益

### 1. 加新東西不用改 code
```sql
-- 加 intent 例句
INSERT INTO intent_anchor (intent, example, language) VALUES (...);

-- 加 prompt 規則
INSERT INTO prompt_rule (topic, trigger_phrase, rule_text, priority, language) VALUES (...);

-- 加關鍵字
INSERT INTO lexicon (kind, word, language) VALUES (...);
```
然後 reload service（或重啟），立即生效。

### 2. Prompt 動態瘦身
- 之前：每次都注入 ~3000 字所有規則
- 現在：always-on (~1200 字) + 相關 conditional (~800 字) = ~2000 字
- **節省 33% token**

### 3. 雙層 RAG
- **rag_example**: 用戶輸入相似的訓練範例（給模型看「別人怎麼處理同類問題」）
- **prompt_rule**: 該情境下的處理規則（給模型看「此類情況應該這樣判斷」）

### 4. 通過率提升
- Baseline (硬編碼 + 無 RAG): **51%**
- 重構後 (DB 驅動 + 雙層 RAG): **76%**
- **+25 個百分點**

## 結構

```
server/
├── app/
│   ├── models/
│   │   ├── intent_anchor.py    ← 新
│   │   ├── prompt_rule.py      ← 新
│   │   ├── lexicon.py          ← 新
│   │   └── rag_example.py      ← 已有
│   ├── repositories/
│   │   ├── intent_anchor_repository.py    ← 新
│   │   ├── prompt_rule_repository.py      ← 新
│   │   ├── lexicon_repository.py          ← 新
│   │   └── rag_repository.py              ← 已有
│   ├── services/
│   │   ├── embedding_service.py    ← 改寫（多 provider cascade）
│   │   ├── semantic_router_service.py  ← 改寫（DB-driven）
│   │   ├── prompt_builder.py       ← 改寫（動態組裝）
│   │   ├── chat_utils.py           ← 改寫（從 lexicon 載入）
│   │   ├── rag_service.py          ← 已有
│   │   └── ai_service.py           ← 微調（embedding cache）
│   └── data/
│       ├── prompt_rules_seed.py    ← 新（22 zh + 3 en 規則）
│       ├── rag_past_schedule.py    ← 新（過期行程範例）
│       └── rag_training_data*.py   ← 已有
├── seed_intent_anchors.py   ← 新
├── seed_prompt_rules.py     ← 新
├── seed_lexicon.py          ← 新
├── reembed_all.py           ← 新（embedding 空間統一）
├── populate_rag.py          ← 已有
├── optimize_rag_from_failures.py  ← 改進（過濾雜訊）
└── run_test_v2.py           ← 新（彈性測試器）
```

## 工作流：未來如何優化

### 加新 intent 講法
```bash
# 用戶開始用新講法（如「記下這件事」）
INSERT INTO intent_anchor (intent, example, language) VALUES ('create', '記下這件事', 'zh-TW');
# 重啟 server 或 semantic_router.reload()
```

### 加新場景處理規則
```python
# 1. 在 app/data/prompt_rules_seed.py 加：
{
    "topic": "recurring_event",
    "priority": 60,
    "trigger_phrase": "每週開會。每月聚餐。每天運動。",
    "rule_text": "## 重複行程\n用戶說「每週/每月」→ 詢問結束日期",
}

# 2. 跑 seed
python seed_prompt_rules.py --reset
```

### 失敗驅動優化迴圈
```bash
# 1. 跑測試
python run_test_v2.py --provider cerebras --n 90 --rag

# 2. 自動回灌真正可學的失敗（過濾掉雜訊）
cd server && python optimize_rag_from_failures.py

# 3. 重跑直到 plateau
```

## 已知限制

1. **Cerebras free tier 嚴格**：跑 20+ 測試會 rate limit。實務需要：
   - 升級 Cerebras 付費方案，或
   - 使用其他中文良好的 LLM（HF Qwen 對中文好但偶爾不穩）

2. **Embedding 空間混亂**：當 Jina / Voyage / Gemini 輪流失敗，新範例會落到不同向量空間，相似度搜尋變不準。
   - 解法：定期跑 `python reembed_all.py` 統一空間

3. **失敗驅動有上限**：第一輪能漲 5-8 個百分點，後續會 plateau。要進一步提升需：
   - 手動寫專門訓練檔案（如 `rag_past_schedule.py` 模式）
   - 或考慮 fine-tune

## 三個關鍵守則

1. **加範例優先於改 code**：99% 的優化只需要 INSERT 一行
2. **A/B 測試容易**：`UPDATE prompt_rule SET enabled = false WHERE topic = 'xxx'` 即可
3. **失敗回灌要過濾**：別把 ERROR 或重複測試結果當訓練資料
