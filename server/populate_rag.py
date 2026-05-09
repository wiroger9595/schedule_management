"""Populate RAG examples from training data files."""

import sys
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session
from app.db.database import engine
from app.repositories.rag_repository import RAGRepository

# Chinese datasets (V1 + V2 + V3)
from app.data.rag_training_data import RAG_TRAINING_DATA
from app.data.rag_training_data_v2 import RAG_TRAINING_DATA_V2
from app.data.rag_training_data_v3 import RAG_TRAINING_DATA_V3

# English datasets (V1 + V2 + V3)
from app.data.rag_training_data_en import RAG_TRAINING_DATA_EN
from app.data.rag_training_data_en_v2 import RAG_TRAINING_DATA_EN_V2
from app.data.rag_training_data_en_v3 import RAG_TRAINING_DATA_EN_V3

# 過期行程處理（針對 past_schedule 失敗類別）
from app.data.rag_past_schedule import RAG_PAST_SCHEDULE_ZH, RAG_PAST_SCHEDULE_EN


def populate_from_dataset(dataset, language: str):
    """Insert dataset into database."""
    session = Session(engine)
    repo = RAGRepository(session)

    examples = []
    for item in dataset:
        # Skip non-example items (helper functions, comments, etc.)
        if not isinstance(item, dict):
            continue
        if "user_message" not in item and "input" not in item:
            continue

        user_message = item.get("user_message") or item.get("input") or ""
        if not user_message:
            continue

        example = {
            "category": item.get("scenario", item.get("category", "general")),
            "user_message": user_message,
            "intent": item.get("intent", "create"),
            "is_complete": item.get("is_complete", False),
            "parsed_data": item.get("parsed", item.get("parsed_data", {})),
            "context": item.get("context", {}),
        }
        examples.append(example)

    if not examples:
        print(f"No examples found in dataset for {language}")
        session.close()
        return 0

    count = repo.add_batch(examples, language=language)
    print(f"✓ Inserted {count} {language} examples")
    session.close()
    return count


def clear_existing():
    """Remove all existing RAG examples."""
    import os
    from sqlalchemy import text
    schema = os.getenv("POSTGRES_SCHEMA", "public")
    session = Session(engine)
    session.execute(text(f"DELETE FROM {schema}.rag_example"))
    session.commit()
    print("🗑️  Cleared existing RAG examples\n")
    session.close()


def main():
    print("🚀 Populating RAG training examples...\n")

    if "--clear" in sys.argv or "--reset" in sys.argv:
        clear_existing()

    zh_total = 0
    en_total = 0

    # Chinese datasets
    for name, dataset in [
        ("zh V1", RAG_TRAINING_DATA),
        ("zh V2", RAG_TRAINING_DATA_V2),
        ("zh V3", RAG_TRAINING_DATA_V3),
        ("zh past_schedule", RAG_PAST_SCHEDULE_ZH),
    ]:
        try:
            count = populate_from_dataset(dataset, "zh-TW")
            zh_total += count
            print(f"  → {name}: {count}")
        except Exception as e:
            print(f"❌ {name} error: {e}")

    # English datasets
    for name, dataset in [
        ("en V1", RAG_TRAINING_DATA_EN),
        ("en V2", RAG_TRAINING_DATA_EN_V2),
        ("en V3", RAG_TRAINING_DATA_EN_V3),
        ("en past_schedule", RAG_PAST_SCHEDULE_EN),
    ]:
        try:
            count = populate_from_dataset(dataset, "en")
            en_total += count
            print(f"  → {name}: {count}")
        except Exception as e:
            print(f"❌ {name} error: {e}")

    total = zh_total + en_total
    if total > 0:
        print(f"\n✅ Total {total} RAG examples inserted ({zh_total} zh + {en_total} en)")
        print("\nRAG is now ready! The AI will use similar examples to improve responses.")
    else:
        print("\n⚠️  No examples were inserted.")


if __name__ == "__main__":
    main()
