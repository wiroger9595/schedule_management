"""
種子資料：把 prompt_rules_seed.py 灌進 prompt_rule 表。
跑完後 prompt_builder 會自動從 DB 讀取規則，不再寫死在程式裡。

用法：
    python seed_prompt_rules.py            # 加入
    python seed_prompt_rules.py --reset    # 清空後重灌
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from sqlalchemy import text
from app.db.database import engine
from app.repositories.prompt_rule_repository import PromptRuleRepository
from app.data.prompt_rules_seed import PROMPT_RULES_ZH, PROMPT_RULES_EN


def reset_table():
    schema = os.getenv("POSTGRES_SCHEMA", "public")
    session = Session(engine)
    session.execute(text(f"DELETE FROM {schema}.prompt_rule"))
    session.commit()
    session.close()
    print("🗑️  Cleared prompt_rule table")


def seed():
    session = Session(engine)
    repo = PromptRuleRepository(session)

    # 加 language 標記
    items_zh = [{**r, "language": "zh-TW"} for r in PROMPT_RULES_ZH]
    items_en = [{**r, "language": "en"} for r in PROMPT_RULES_EN]

    n_zh = repo.add_batch(items_zh)
    print(f"✅ Inserted {n_zh} zh-TW prompt rules")

    n_en = repo.add_batch(items_en)
    print(f"✅ Inserted {n_en} en prompt rules")

    # 統計
    always_on_zh = sum(1 for r in PROMPT_RULES_ZH if r.get("priority", 0) >= 100)
    cond_zh = len(PROMPT_RULES_ZH) - always_on_zh
    print(f"\n📊 zh-TW: {always_on_zh} always-on + {cond_zh} conditional")

    session.close()


def main():
    if "--reset" in sys.argv:
        reset_table()
    seed()
    print("\n下次請求 system_prompt 會自動從 DB 載入規則。")
    print("加新規則: INSERT 進 prompt_rule 表（不用改 code、不用重啟）")


if __name__ == "__main__":
    main()
