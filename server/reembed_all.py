"""
重新 embed 所有 RAG 資料，統一用同一個 provider。
解決混用 HF/Jina/Gemini 時 embedding 空間不一致的問題。
"""
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")

import sys
from sqlmodel import Session, select
from app.db.database import engine
from app.models.rag_example import RAGExample
from app.models.intent_anchor import IntentAnchor
from app.models.prompt_rule import PromptRule
from app.services.embedding_service import EmbeddingService

# 每個 model 的 embedding 來源文字欄位
_TEXT_FIELDS = {
    RAGExample: "user_message",
    IntentAnchor: "example",
    PromptRule: "trigger_phrase",
}


def reembed_table(session, model_class, label):
    rows = session.exec(select(model_class)).all()
    print(f"\n📦 {label}: {len(rows)} rows")

    text_field = _TEXT_FIELDS[model_class]

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
    reembed_table(session, PromptRule, "prompt_rule")

    session.close()
    print("\n✅ 完成！所有向量現在在同一個 embedding 空間。")
    print("⚠️ 別忘了行程/聯絡人向量：python reindex_all_embeddings.py")


if __name__ == "__main__":
    main()
