"""
種子資料：把 chat_utils.py 的硬編碼字典灌進 lexicon 表。

未來新增詞：
    INSERT INTO lexicon (kind, word, language) VALUES ('stop_word', '新詞', 'zh-TW');
    然後 reload_lexicon_cache() 或重啟 server。
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from sqlalchemy import text
from app.db.database import engine
from app.repositories.lexicon_repository import LexiconRepository, reload_lexicon_cache


# ── 從原本的硬編碼遷移 ────────────────────────────────────────────────
NON_NAMES_ZH = {
    "我", "你", "他", "她", "他們", "大家", "朋友", "同事", "家人",
    "老闆", "客戶", "你們", "我們",
}
STOP_WORDS_ZH = {
    "取消", "刪除", "刪掉", "移除", "更改", "修改", "調整", "把", "的", "行程",
    "活動", "我", "這個", "請", "幫我", "改到", "延後", "提早",
}

# 加英文版（之前漏了）
NON_NAMES_EN = {"i", "you", "he", "she", "they", "we", "us", "everyone",
                "friend", "friends", "colleague", "colleagues", "boss", "client"}
STOP_WORDS_EN = {"cancel", "delete", "remove", "change", "modify", "edit",
                 "the", "a", "an", "schedule", "event", "please", "to"}


def reset_table():
    schema = os.getenv("POSTGRES_SCHEMA", "public")
    session = Session(engine)
    session.execute(text(f"DELETE FROM {schema}.lexicon"))
    session.commit()
    session.close()
    print("🗑️  Cleared lexicon table")


def seed():
    session = Session(engine)
    repo = LexiconRepository(session)

    n = 0
    n += repo.add_batch("non_name",  list(NON_NAMES_ZH),  "zh-TW")
    n += repo.add_batch("stop_word", list(STOP_WORDS_ZH), "zh-TW")
    n += repo.add_batch("non_name",  list(NON_NAMES_EN),  "en")
    n += repo.add_batch("stop_word", list(STOP_WORDS_EN), "en")

    print(f"✅ Inserted {n} lexicon entries")
    print(f"  • non_name (zh):  {len(NON_NAMES_ZH)}")
    print(f"  • stop_word (zh): {len(STOP_WORDS_ZH)}")
    print(f"  • non_name (en):  {len(NON_NAMES_EN)}")
    print(f"  • stop_word (en): {len(STOP_WORDS_EN)}")

    reload_lexicon_cache()
    session.close()


def main():
    if "--reset" in sys.argv:
        reset_table()
    seed()
    print("\n下次請求 chat_utils 會自動從 DB 載入字典。")


if __name__ == "__main__":
    main()
