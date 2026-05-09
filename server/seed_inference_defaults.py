"""
種子資料：把 prompt_rules_seed.py 文字裡的 mapping 抽取成結構化資料。

之前：規則寫成 markdown「吃飯→19:00, 開會→09:00...」
現在：每個 mapping 一行 INSERT，可獨立改、可程式化讀取
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from sqlalchemy import text
from app.db.database import engine
from app.repositories.inference_default_repository import InferenceDefaultRepository, reload_inference_cache


# ─────────────────────────────────────────────────────────────────────
# 1. activity_time: 活動 → 預設時間
# ─────────────────────────────────────────────────────────────────────
ACTIVITY_TIME_ZH = [
    {"keywords": ["早餐", "早午餐", "brunch"], "result": "09:00:00", "priority": 90},
    {"keywords": ["午餐", "中餐"], "result": "12:00:00", "priority": 90},
    {"keywords": ["下午茶", "afternoon tea"], "result": "15:00:00", "priority": 95},  # 比晚餐更具體
    {"keywords": ["晚餐", "聚餐", "宵夜"], "result": "19:00:00", "priority": 90},
    {"keywords": ["吃飯", "用餐", "用膳", "進食"], "result": "19:00:00", "priority": 70, "fallback_result": "12:00:00"},  # 吃飯較模糊，看上下文
    {"keywords": ["開會", "會議", "討論", "報告", "簡報"], "result": "09:00:00", "priority": 90},
    {"keywords": ["1on1", "面談", "面試"], "result": "10:00:00", "priority": 95},
    {"keywords": ["運動", "打球", "跑步", "健身", "游泳", "瑜伽"], "result": "15:00:00", "priority": 85},
    {"keywords": ["看電影", "電影", "看戲", "演唱會", "音樂會"], "result": "19:00:00", "priority": 85},
    {"keywords": ["逛街", "購物", "shopping"], "result": "14:00:00", "priority": 80},
    {"keywords": ["看診", "看醫生", "掛號", "檢查", "健檢"], "result": "10:00:00", "priority": 85},
    {"keywords": ["上課", "進修", "補習"], "result": "09:00:00", "priority": 80},
    {"keywords": ["接送", "送小孩"], "result": "07:30:00", "priority": 85},
    {"keywords": ["旅遊", "出遊", "出差"], "result": "08:00:00", "priority": 80},
    {"keywords": ["搭飛機", "搭機", "航班"], "result": "08:00:00", "priority": 85},
]

ACTIVITY_TIME_EN = [
    {"keywords": ["breakfast", "brunch"], "result": "09:00:00", "priority": 90},
    {"keywords": ["lunch"], "result": "12:00:00", "priority": 90},
    {"keywords": ["afternoon tea", "tea"], "result": "15:00:00", "priority": 90},
    {"keywords": ["dinner", "supper"], "result": "19:00:00", "priority": 90},
    {"keywords": ["meeting", "discussion"], "result": "09:00:00", "priority": 90},
    {"keywords": ["interview", "1on1"], "result": "10:00:00", "priority": 95},
    {"keywords": ["workout", "gym", "running", "swimming", "yoga"], "result": "15:00:00", "priority": 85},
    {"keywords": ["movie", "concert"], "result": "19:00:00", "priority": 85},
    {"keywords": ["shopping"], "result": "14:00:00", "priority": 80},
    {"keywords": ["doctor", "appointment", "checkup"], "result": "10:00:00", "priority": 85},
]


# ─────────────────────────────────────────────────────────────────────
# 2. tod_time: 時段詞 → 預設時間
# ─────────────────────────────────────────────────────────────────────
TOD_TIME_ZH = [
    {"keywords": ["凌晨", "深夜"], "result": "02:00:00", "priority": 90},
    {"keywords": ["清晨", "一大早"], "result": "06:00:00", "priority": 95},
    {"keywords": ["早上", "上午", "早晨"], "result": "09:00:00", "priority": 80},
    {"keywords": ["中午", "正午"], "result": "12:00:00", "priority": 90},
    {"keywords": ["下午"], "result": "14:00:00", "priority": 80},
    {"keywords": ["傍晚", "黃昏"], "result": "17:00:00", "priority": 90},
    {"keywords": ["晚上", "夜晚"], "result": "19:00:00", "priority": 80},
    {"keywords": ["半夜"], "result": "00:00:00", "priority": 90},
]

TOD_TIME_EN = [
    {"keywords": ["dawn", "early morning"], "result": "06:00:00", "priority": 95},
    {"keywords": ["morning"], "result": "09:00:00", "priority": 80},
    {"keywords": ["noon", "midday"], "result": "12:00:00", "priority": 90},
    {"keywords": ["afternoon"], "result": "14:00:00", "priority": 80},
    {"keywords": ["evening"], "result": "18:00:00", "priority": 85},
    {"keywords": ["night"], "result": "20:00:00", "priority": 80},
    {"keywords": ["late night", "midnight"], "result": "23:00:00", "priority": 85},
]


# ─────────────────────────────────────────────────────────────────────
# 3. title_template: 活動 → title 生成模板
# {person} 會被替換成參與者名（無人名時用 fallback_result）
# ─────────────────────────────────────────────────────────────────────
TITLE_TEMPLATE_ZH = [
    {"keywords": ["吃飯", "聚餐", "用餐"], "result": "與{person}吃飯", "fallback_result": "聚餐", "priority": 80},
    {"keywords": ["午餐"], "result": "與{person}午餐", "fallback_result": "午餐", "priority": 85},
    {"keywords": ["晚餐"], "result": "與{person}晚餐", "fallback_result": "晚餐", "priority": 85},
    {"keywords": ["開會", "會議"], "result": "與{person}開會", "fallback_result": "開會", "priority": 85},
    {"keywords": ["討論"], "result": "與{person}討論", "fallback_result": "討論會", "priority": 80},
    {"keywords": ["看電影"], "result": "看電影", "fallback_result": "看電影", "priority": 85},
    {"keywords": ["演唱會"], "result": "看{person}演唱會", "fallback_result": "演唱會", "priority": 85},
    {"keywords": ["打球", "球賽"], "result": "打球", "fallback_result": "打球", "priority": 85},
    {"keywords": ["健身", "運動"], "result": "健身", "fallback_result": "健身", "priority": 80},
    {"keywords": ["逛街", "購物"], "result": "逛街", "fallback_result": "逛街", "priority": 80},
    {"keywords": ["旅遊", "出遊"], "result": "出遊", "fallback_result": "出遊", "priority": 80},
    {"keywords": ["搭飛機", "搭機"], "result": "搭飛機", "fallback_result": "搭飛機", "priority": 85},
    {"keywords": ["看醫生", "看診"], "result": "看{person}醫生", "fallback_result": "看醫生", "priority": 85},
    {"keywords": ["上課"], "result": "上{person}課", "fallback_result": "上課", "priority": 80},
]


# ─────────────────────────────────────────────────────────────────────
# 4. duration: 活動 → 預設時長
# ─────────────────────────────────────────────────────────────────────
DURATION_ZH = [
    {"keywords": ["早餐", "早午餐"], "result": "01:00:00", "priority": 85},
    {"keywords": ["午餐", "晚餐", "聚餐"], "result": "01:30:00", "priority": 85},
    {"keywords": ["吃飯"], "result": "01:30:00", "priority": 70},
    {"keywords": ["下午茶"], "result": "01:30:00", "priority": 90},
    {"keywords": ["開會", "會議", "討論"], "result": "01:00:00", "priority": 85},
    {"keywords": ["1on1", "面試"], "result": "00:30:00", "priority": 90},
    {"keywords": ["看電影"], "result": "02:30:00", "priority": 85},
    {"keywords": ["演唱會"], "result": "03:00:00", "priority": 85},
    {"keywords": ["健身", "運動", "打球"], "result": "01:30:00", "priority": 80},
    {"keywords": ["看診", "看醫生"], "result": "00:30:00", "priority": 85},
    {"keywords": ["上課"], "result": "02:00:00", "priority": 80},
    {"keywords": ["逛街", "購物"], "result": "02:00:00", "priority": 80},
]


def reset_table():
    schema = os.getenv("POSTGRES_SCHEMA", "public")
    session = Session(engine)
    session.execute(text(f"DELETE FROM {schema}.inference_default"))
    session.commit()
    session.close()
    print("🗑️  Cleared inference_default table")


def seed():
    session = Session(engine)
    repo = InferenceDefaultRepository(session)

    items = []
    # zh-TW
    for x in ACTIVITY_TIME_ZH:    items.append({"kind": "activity_time", "language": "zh-TW", **x})
    for x in TOD_TIME_ZH:         items.append({"kind": "tod_time",      "language": "zh-TW", **x})
    for x in TITLE_TEMPLATE_ZH:   items.append({"kind": "title_template","language": "zh-TW", **x})
    for x in DURATION_ZH:         items.append({"kind": "duration",      "language": "zh-TW", **x})
    # en
    for x in ACTIVITY_TIME_EN:    items.append({"kind": "activity_time", "language": "en", **x})
    for x in TOD_TIME_EN:         items.append({"kind": "tod_time",      "language": "en", **x})

    n = repo.add_batch(items)
    print(f"✅ Inserted {n} inference defaults")
    print(f"  • activity_time:  {len(ACTIVITY_TIME_ZH)} zh + {len(ACTIVITY_TIME_EN)} en")
    print(f"  • tod_time:       {len(TOD_TIME_ZH)} zh + {len(TOD_TIME_EN)} en")
    print(f"  • title_template: {len(TITLE_TEMPLATE_ZH)} zh")
    print(f"  • duration:       {len(DURATION_ZH)} zh")

    reload_inference_cache()
    session.close()


def main():
    if "--reset" in sys.argv:
        reset_table()
    seed()
    print("\n下次請求 prompt_builder 會自動從 DB 載入這些預設值。")
    print("加新映射: INSERT 進 inference_default 表（不用改 code、不用重啟）")


if __name__ == "__main__":
    main()
