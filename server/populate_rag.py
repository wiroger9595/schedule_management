"""Populate RAG examples from training data files."""

import sys
from app.db.database import SessionLocal
from app.repositories.rag_repository import RAGRepository
from app.data.rag_training_data import RAG_TRAINING_DATA  # Chinese V3
from app.data.rag_training_data_en_v3 import RAG_TRAINING_DATA_EN_V3  # English V3


def populate_from_dataset(dataset, language: str):
    """Insert dataset into database."""
    session = SessionLocal()
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


def main():
    print("🚀 Populating RAG training examples...\n")

    # Check if datasets are available
    try:
        zh_count = populate_from_dataset(RAG_TRAINING_DATA, "zh-TW")
    except Exception as e:
        print(f"❌ Chinese dataset error: {e}")
        zh_count = 0

    try:
        en_count = populate_from_dataset(RAG_TRAINING_DATA_EN_V3, "en")
    except Exception as e:
        print(f"❌ English dataset error: {e}")
        en_count = 0

    total = zh_count + en_count
    if total > 0:
        print(f"\n✅ Total {total} RAG examples inserted successfully")
        print("\nRAG is now ready! The AI will use similar examples to improve responses.")
    else:
        print("\n⚠️  No examples were inserted. Check that training data files exist.")


if __name__ == "__main__":
    main()
