# RAG 訓練範例建立指南

完整流程：從「發現問題」到「自己建一份訓練檔案」。

---

## 📐 一、RAG 範例的基本結構

每個範例對應「用戶這樣說 → AI 應該這樣判斷」的對應關係。

### 最小欄位

```python
{
    "user_message": "明天下午三點開會",      # 用戶說什麼（必填）
    "intent": "create",                    # 意圖：create/edit/delete/query（必填）
    "is_complete": False,                  # 資訊是否齊全可執行（必填）
}
```

### 完整欄位（推薦）

```python
{
    # ─── 基本（必填）───
    "scenario": "個人開會 - 缺地點",          # 場景說明，方便除錯
    "user_message": "明天下午三點開會",
    "intent": "create",
    "is_complete": False,

    # ─── 上下文（重要）───
    "context": {
        "schedule_list": [...],            # 用戶現有行程清單
        "current_time": "2026-05-09T10:00", # 假設的當前時間
        "_pending_edit_schedule_id": "abc", # 是否在編輯中
    },

    # ─── 預期動作（增強學習效果）───
    "expected_action": "ask_user",
    "expected_question": "請問要在哪裡開會？",
    "parsed_data": {
        "title": "開會",
        "start_time": "2026-05-10T15:00:00"
    },

    # ─── 教學（最有用）───
    "rule": "個人行程必須有 location 才完整",
    "WRONG": "create_schedule(...) 沒有 location",
    "CORRECT": "ask_user 追問地點",
    "explanation": "個人行程不需要 participants，但必須有 title+time+location",
}
```

### 各欄位的作用

| 欄位 | 作用 | 必填 |
|------|------|------|
| `user_message` | 被 embedding 用來查相似性 | ✅ |
| `intent` | 模型學習如何分類 | ✅ |
| `is_complete` | 判斷是否該執行還是追問 | ✅ |
| `scenario` | 你和未來的自己除錯時用 | 推薦 |
| `rule` | 用一句話總結原則（注入 prompt 給模型看）| 推薦 |
| `WRONG/CORRECT` | 反例對比，最有教學效果 | 推薦 |
| `parsed_data` | 預期解析結果 | 編輯時用 |
| `context` | 模擬真實情境 | 修改場景必填 |

---

## 🔄 二、完整工作流（5 步驟）

### Step 1: 找出失敗案例

跑測試後，檢查資料庫看哪些失敗：

```bash
cd /Users/chenrobert/Documents/code_life/schedule_management
python run_test_v2.py --provider cerebras --n 90 --rag
```

然後查失敗模式：

```python
# 從 Python shell 或寫個小腳本
from sqlmodel import Session, select
from app.db.database import engine
from app.models.ai_test_result import AITestResult
from collections import Counter

session = Session(engine)
recent = session.exec(
    select(AITestResult)
    .order_by(AITestResult.created_at.desc())
    .limit(90)
).all()

# 按類別看失敗
fail_by_cat = Counter(r.category for r in recent if not r.passed)
print(fail_by_cat.most_common())

# 看失敗的 user_message
for r in recent:
    if not r.passed:
        print(f"[{r.category}] {r.user_message}")
        print(f"  期望: intent={r.expected_intent}, complete={r.expected_complete}")
        print(f"  實際: intent={r.actual_intent}, complete={r.actual_complete}")
```

### Step 2: 分析失敗原因

針對每個失敗案例，問自己三個問題：

1. **是 intent 判斷錯？** → 例子裡多放對的 intent
2. **是 is_complete 判斷錯？** → 例子裡強調哪些欄位該齊全
3. **是欄位提取錯？** → `parsed_data` 寫清楚正確結果

### Step 3: 建立訓練檔案

按主題建一份新檔案（推薦命名：`rag_<topic>.py`）：

```bash
cd server/app/data
touch rag_<your_topic>.py
```

範例骨架：

```python
"""
RAG 訓練資料：<主題>
場景：<簡短描述為什麼需要這份資料>
"""

TODAY = "2026-05-09"  # 假設今天

RAG_<TOPIC>_ZH = [
    # ============================================================
    # 場景 1：<說明>
    # ============================================================
    {
        "scenario": "<場景名稱>",
        "user_message": "<用戶輸入>",
        "intent": "create",
        "is_complete": False,
        "rule": "<一句話原則>",
        "WRONG": "<錯誤行為>",
        "CORRECT": "<正確行為>",
    },
    # ... 更多範例
]

RAG_<TOPIC>_EN = [
    # 對應的英文版
]


def stats():
    print(f"<TOPIC>: zh={len(RAG_<TOPIC>_ZH)}, en={len(RAG_<TOPIC>_EN)}")


if __name__ == "__main__":
    stats()
```

### Step 4: 灌入資料庫

寫個一次性腳本（或修改 `populate_rag.py`）：

```python
# server/load_my_examples.py
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from sqlalchemy import text
from app.db.database import engine
from app.repositories.rag_repository import RAGRepository
from app.data.rag_<topic> import RAG_<TOPIC>_ZH, RAG_<TOPIC>_EN

session = Session(engine)
repo = RAGRepository(session)

# 先清掉舊的（可選，避免重複）
import os
schema = os.getenv('POSTGRES_SCHEMA', 'public')
session.execute(text(f"DELETE FROM {schema}.rag_example WHERE category = '<topic>'"))
session.commit()

def to_db_format(dataset):
    return [{
        'category': '<topic>',
        'user_message': item['user_message'],
        'intent': item.get('intent', 'create'),
        'is_complete': item.get('is_complete', False),
        'parsed_data': item.get('parsed_data') or {'rule': item.get('rule', '')[:200]},
        'context': item.get('context', {}),
    } for item in dataset]

zh_n = repo.add_batch(to_db_format(RAG_<TOPIC>_ZH), language='zh-TW')
en_n = repo.add_batch(to_db_format(RAG_<TOPIC>_EN), language='en')
print(f'✓ {zh_n} zh + {en_n} en 已加入 RAG')
session.close()
```

執行：
```bash
cd server && python load_my_examples.py
```

### Step 5: 驗證效果

只跑相關類別的測試（節省時間）：

```bash
# 跑全部，檢查特定類別的通過率
python run_test_v2.py --provider cerebras --n 90 --rag

# 然後查那個類別
python -c "
from dotenv import load_dotenv
load_dotenv('server/.env')
from sqlmodel import Session, select
import sys; sys.path.insert(0, 'server')
from app.db.database import engine
from app.models.ai_test_result import AITestResult

session = Session(engine)
recent = session.exec(
    select(AITestResult)
    .where(AITestResult.category == '<topic>')
    .order_by(AITestResult.created_at.desc())
    .limit(20)
).all()
passed = sum(1 for r in recent if r.passed)
print(f'<topic>: {passed}/{len(recent)} = {passed*100/len(recent):.0f}%')
"
```

---

## 📝 三、如何寫出「好」範例

### ✅ 好範例的 5 個特徵

**1. 涵蓋邊界**
```python
# ❌ 只有正常情況
{"user_message": "明天3點開會", "intent": "create", "is_complete": False}

# ✅ 有邊界情況
{"user_message": "明天3點開會", "intent": "create", "is_complete": False},
{"user_message": "現在", "intent": "ask_user", "is_complete": False},  # 模糊
{"user_message": "下週某天", "intent": "create", "is_complete": False},  # 不確定
```

**2. 對比組（最有效）**

成對的「相似輸入但不同結果」幫模型學會差別：

```python
# 個人 vs 多人 對比
{"user_message": "明天3點打球",
 "intent": "create", "is_complete": False,  # 缺地點
 "rule": "個人行程需要 title+time+location"},

{"user_message": "明天3點在大安公園打球",
 "intent": "create", "is_complete": True,   # 齊全
 "rule": "個人行程不需要 participants"},

{"user_message": "明天3點跟小明在大安公園打球",
 "intent": "create", "is_complete": True,
 "rule": "多人行程需要 participants（已給）"},

{"user_message": "明天3點跟小明打球",
 "intent": "create", "is_complete": False,  # 缺地點
 "rule": "多人行程也要 location"},
```

**3. 包含 `rule` 解釋**

`rule` 會被注入到 prompt 中，模型直接看得到原則：

```python
# ❌ 沒解釋
{"user_message": "改到下午", "intent": "edit", "is_complete": False}

# ✅ 有解釋
{"user_message": "改到下午",
 "intent": "edit", "is_complete": False,
 "rule": "「改到」+ 模糊時段 → 必須追問具體時間"}
```

**4. 使用 `WRONG/CORRECT` 反例**

模型學「不要做什麼」比「該做什麼」更有效：

```python
{
    "user_message": "把昨天的會議改成3點",
    "intent": "edit", "is_complete": False,
    "WRONG": "update_schedule(start_time='2026-05-08T15:00:00') 把過去時間又改成過去",
    "CORRECT": "ask_user('原會議已過期，改到哪一天的3點？')",
    "rule": "過期行程改時間必須詢問新日期",
}
```

**5. 真實的 `context`**

如果情境涉及行程清單、編輯狀態等，要給對：

```python
{
    "user_message": "改到3點",
    "context": {
        "schedule_list": [
            {"id": "abc", "title": "會議", "start_time": "2026-05-10T10:00"}
        ],
        "_pending_edit_schedule_id": "abc",  # 表示正在編輯
    },
    "intent": "edit",
    "is_complete": True,
    "parsed_data": {"schedule_id": "abc", "start_time": "2026-05-10T15:00:00"},
}
```

### ❌ 常見錯誤

**錯誤 1：太抽象**
```python
# ❌ 模型看不出何時該套用
{"user_message": "幫我安排", "intent": "create"}

# ✅ 具體場景
{"user_message": "幫我安排明天的會議",
 "intent": "create", "is_complete": False,
 "rule": "缺時間/地點 → 一次追問所有缺的"}
```

**錯誤 2：與既有範例衝突**

加之前先 grep 看有沒有矛盾：
```bash
grep -r "明天.*打球" server/app/data/rag_*.py
```

**錯誤 3：忘記英文版**

中英都用同一個 RAG，要兩種語言都覆蓋：
```python
RAG_TOPIC_ZH = [...]
RAG_TOPIC_EN = [...]  # 對應的英文版
```

---

## 🎯 四、主題範例：完整實戰

假設你發現「使用者用簡寫」常失敗，建一份：

```python
# server/app/data/rag_abbreviations.py
"""
RAG 訓練資料：簡寫和俚語
場景：用戶常用 tmrw, brb, 之類的簡寫，模型常認不出
"""

RAG_ABBR_ZH = [
    {
        "scenario": "tmrw = 明天",
        "user_message": "tmrw 3pm 開會",
        "intent": "create",
        "is_complete": False,
        "parsed_data": {"start_time": "2026-05-10T15:00:00", "title": "開會"},
        "rule": "tmrw=tomorrow=明天",
    },
    {
        "scenario": "中英混用",
        "user_message": "明天 lunch with @小明",
        "intent": "create",
        "is_complete": False,
        "parsed_data": {"title": "與小明午餐", "participants": ["@小明"]},
        "rule": "lunch=午餐，預設12:00",
    },
    {
        "scenario": "縮寫地名",
        "user_message": "明天3點 101 開會",
        "intent": "create",
        "is_complete": True,
        "parsed_data": {"location": "台北101", "title": "開會"},
        "rule": "101 = 台北101，常見地標縮寫",
    },
    # ... 更多
]

RAG_ABBR_EN = [
    {
        "scenario": "tmrw shorthand",
        "user_message": "tmrw 3pm meeting",
        "intent": "create",
        "is_complete": False,
        "rule": "tmrw = tomorrow",
    },
    {
        "scenario": "EOD = end of day",
        "user_message": "Send the report by EOD",
        "intent": "create",
        "is_complete": False,
        "rule": "EOD = today 18:00, ask if reminder vs schedule",
    },
    # ... 更多
]


def stats():
    print(f"abbreviations: zh={len(RAG_ABBR_ZH)}, en={len(RAG_ABBR_EN)}")
```

加入 DB：

```python
# 一次性腳本
from dotenv import load_dotenv; load_dotenv()
from sqlmodel import Session
from app.db.database import engine
from app.repositories.rag_repository import RAGRepository
from app.data.rag_abbreviations import RAG_ABBR_ZH, RAG_ABBR_EN

session = Session(engine)
repo = RAGRepository(session)

repo.add_batch([{
    'category': 'abbreviations',
    'user_message': x['user_message'],
    'intent': x['intent'],
    'is_complete': x['is_complete'],
    'parsed_data': x.get('parsed_data', {'rule': x.get('rule', '')}),
} for x in RAG_ABBR_ZH], language='zh-TW')

repo.add_batch([{
    'category': 'abbreviations',
    'user_message': x['user_message'],
    'intent': x['intent'],
    'is_complete': x['is_complete'],
    'parsed_data': x.get('parsed_data', {'rule': x.get('rule', '')}),
} for x in RAG_ABBR_EN], language='en')

session.commit()
session.close()
```

---

## 🔁 五、失敗驅動的迭代循環

最有效的優化方式：

```
1. 跑測試 → 看失敗
   python run_test_v2.py --provider cerebras --n 90 --rag

2. 自動回灌（把失敗的當訓練資料）
   cd server && python optimize_rag_from_failures.py

3. 重跑測試
   python run_test_v2.py --provider cerebras --n 90 --rag

4. 看分數有沒有提升
   - 有 → 繼續第 2 步（直到不再提升）
   - 停滯 → 寫專門的訓練檔案（看下面 step 5）

5. 分析剩餘失敗類別
   - 哪個類別失敗最多？(edge_case? parsing?)
   - 寫專門的 RAG 檔案（按本指南 step 3）
   
6. 回到第 1 步
```

每輪預期改進：
- Round 1：51% → ~58%（加入 V1+V2+V3 基礎範例）
- Round 2：58% → ~62%（自動回灌失敗案例）
- Round 3：62% → ~67%（針對 past_schedule 補強）
- Round 4：67% → ~72%（針對 edge_case/parsing 補強）
- 第 5 輪後通常會 plateau，那就考慮 fine-tune

---

## 🔧 六、檢查清單（每次新增範例時）

寫完一份新的訓練檔案，照這個檢查：

- [ ] 中文版和英文版都有
- [ ] 至少 10 個範例（少了不夠模型學）
- [ ] 包含正反對比組（成對的相似輸入）
- [ ] 每個範例都有 `rule` 或 `explanation`
- [ ] 邊界情況有覆蓋（空資料、模糊輸入）
- [ ] 涉及修改/刪除的有 `context.schedule_list`
- [ ] 跟既有範例不衝突（grep 過了）
- [ ] 灌入 DB 後跑測試驗證有效

---

## 📋 七、現有訓練檔案參考

| 檔案 | 主題 | 數量 |
|------|------|------|
| `rag_training_data.py` (V1) | 中文基礎 | 67 |
| `rag_training_data_v2.py` (V2) | 中文真實場景 | 53 |
| `rag_training_data_v3.py` (V3) | 中文失敗修正 | 66 |
| `rag_training_data_en.py` | 英文基礎 | 67 |
| `rag_training_data_en_v2.py` | 英文真實場景 | 53 |
| `rag_training_data_en_v3.py` | 英文失敗修正 | 68 |
| **`rag_past_schedule.py`** | **過期行程** | **23** |

需要補的（按優先順序）：
- `rag_edge_cases.py` —— 邊界情況（空輸入、超長輸入、特殊字符）
- `rag_parsing.py` —— 時間/地點解析難例
- `rag_location.py` —— 地點歧義（連鎖店、模糊地址）
- `rag_validation.py` —— 資料驗證（衝突偵測、重複行程）
- `rag_intent.py` —— 意圖判斷邊界（query vs create）

---

## 🎓 重點觀念回顧

1. **RAG 不是訓練模型**，是「給模型看範例幫它做決定」
2. **每個範例都會被 embed**，相似度搜尋在用戶提問時自動觸發
3. **加範例不需要重新訓練**，只要 `add_batch` 進 DB 就生效
4. **品質 > 數量**，10 個精準的對比例子勝過 100 個雷同的
5. **失敗驅動最有效**，把模型錯的當訓練資料

完。
