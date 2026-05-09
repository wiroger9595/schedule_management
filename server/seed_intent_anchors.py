"""
一次性遷移腳本：把硬編碼的 INTENT_EXAMPLES 灌進 intent_anchor 表。
跑完後 semantic_router 會自動從 DB 讀取，不再需要修改程式碼。

用法：
    python seed_intent_anchors.py            # 加入（重複會跳過）
    python seed_intent_anchors.py --reset    # 清空後重灌
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from sqlalchemy import text
from app.db.database import engine
from app.repositories.intent_anchor_repository import IntentAnchorRepository


# 從原本的硬編碼遷移過來
INTENT_EXAMPLES_ZH = {
    "create": [
        "幫我安排明天下午三點的會議",
        "新增一個行程",
        "我要約人吃飯",
        "記錄一下週五打球",
        "安排一個活動",
        "建立行程",
        "我要預約",
        "下週二跟客戶開會",
        "晚上八點看電影",
        "明天早上九點牙醫",
    ],
    "edit": [
        "把打球時間改到下午五點",
        "更改昨天的會議地點",
        "把跟Robert的約會延後一小時",
        "修改行程",
        "換一個時間",
        "調整一下",
        "改到明天",
        "推遲一個小時",
        "提早半小時",
        "地點換到星巴克",
    ],
    "delete": [
        "取消打球活動",
        "刪除明天的會議",
        "移除那個行程",
        "取消跟王醫生的約",
        "不去了",
        "刪掉",
        "取消這個",
        "移除行程",
    ],
    "query": [
        "我今天有什麼行程",
        "下週有哪些安排",
        "查一下我的行程",
        "找找看跟Robert的約",
        "有什麼活動",
        "什麼時候有空",
        "最近有哪些行程",
    ],
}

# 順便加英文版（之前漏了）
INTENT_EXAMPLES_EN = {
    "create": [
        "schedule a meeting tomorrow at 3pm",
        "add a new event",
        "book dinner with friends",
        "set up a workout on friday",
        "create an event",
        "make a reservation",
        "meeting with client next tuesday",
        "movie at 8pm",
    ],
    "edit": [
        "change the meeting to 5pm",
        "update yesterday's meeting location",
        "postpone the appointment by an hour",
        "modify the schedule",
        "reschedule to tomorrow",
        "move it earlier",
        "change location to Starbucks",
    ],
    "delete": [
        "cancel the basketball game",
        "delete tomorrow's meeting",
        "remove that event",
        "cancel my appointment",
        "skip it",
        "drop the meeting",
    ],
    "query": [
        "what's on my schedule today",
        "what do I have next week",
        "list my events",
        "find my appointment with Robert",
        "when am I free",
    ],
}


def reset_table():
    schema = os.getenv("POSTGRES_SCHEMA", "public")
    session = Session(engine)
    session.execute(text(f"DELETE FROM {schema}.intent_anchor"))
    session.commit()
    session.close()
    print("🗑️  Cleared intent_anchor table")


def seed():
    session = Session(engine)
    repo = IntentAnchorRepository(session)

    items = []
    for intent, examples in INTENT_EXAMPLES_ZH.items():
        for ex in examples:
            items.append({"intent": intent, "example": ex, "language": "zh-TW"})
    for intent, examples in INTENT_EXAMPLES_EN.items():
        for ex in examples:
            items.append({"intent": intent, "example": ex, "language": "en"})

    n = repo.add_batch(items)
    print(f"✅ Inserted {n} intent anchors ({len(INTENT_EXAMPLES_ZH)} zh intents + {len(INTENT_EXAMPLES_EN)} en intents)")
    session.close()


def main():
    if "--reset" in sys.argv:
        reset_table()
    seed()
    print("\n下次重啟 server，semantic_router 會自動從 DB 載入錨點。")


if __name__ == "__main__":
    main()
