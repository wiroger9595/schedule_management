"""
重新 embed 所有 RAG 資料，統一用同一個 provider。
解決混用 HF/Jina/Gemini 時 embedding 空間不一致的問題。
"""
from dotenv import load_dotenv
load_dotenv()

import sys
from sqlmodel import Session, select
from app.db.database import engine
from app.models.rag_example import RAGExample
from app.models.intent_anchor import IntentAnchor
from app.services.embedding_service import EmbeddingService


def reembed_table(session, model_class, label):
    rows = session.exec(select(model_class)).all()
    print(f"\n📦 {label}: {len(rows)} rows")

    # Get text field
    text_field = "user_message" if model_class == RAGExample else "example"

    # Batch in chunks of 50
    for i in range(0, len(rows), 50):
        chunk = rows[i:i+50]
        texts = [getattr(r, text_field) for r in chunk]
        embeddings = EmbeddingService.embed_batch(texts)
        for r, emb in zip(chunk, embeddings):
            r.embedding = emb
            session.add(r)
        session.commit()
        print(f"  ✓ Re-embedded {min(i+50, len(rows))}/{len(rows)}")


def main():
    session = Session(engine)
    print("🔄 重新 embedding 所有資料（用目前 cascade 第一個可用的 provider）")

    reembed_table(session, RAGExample, "rag_example")
    reembed_table(session, IntentAnchor, "intent_anchor")

    session.close()
    print("\n✅ 完成！所有向量現在在同一個 embedding 空間。")


if __name__ == "__main__":
    main()
