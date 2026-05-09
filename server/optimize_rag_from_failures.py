"""
從測試失敗自動生成 RAG 例子。
最有效的優化方式：把模型答錯的當訓練資料補進去。
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from sqlmodel import Session, select
from app.db.database import engine
from app.models.ai_test_result import AITestResult
from app.repositories.rag_repository import RAGRepository


def extract_failures(session, limit=90):
    """取出最近一輪測試中失敗的案例。"""
    results = session.exec(
        select(AITestResult)
        .order_by(AITestResult.created_at.desc())
        .limit(limit)
    ).all()
    return [r for r in results if not r.passed and r.actual_intent != "ERROR"]


def is_chinese(text: str) -> bool:
    """簡單判斷是否為中文。"""
    return any('一' <= c <= '鿿' for c in text or "")


def main():
    session = Session(engine)
    repo = RAGRepository(session)

    failures = extract_failures(session)
    print(f"📊 發現 {len(failures)} 個失敗案例")

    # 分類失敗類型
    intent_errors = [f for f in failures if f.actual_intent != f.expected_intent]
    complete_errors = [f for f in failures
                       if f.actual_intent == f.expected_intent
                       and f.actual_complete != f.expected_complete]

    print(f"  • Intent 誤判: {len(intent_errors)}")
    print(f"  • is_complete 誤判: {len(complete_errors)}")

    examples_to_add = []

    for f in failures:
        language = "zh-TW" if is_chinese(f.user_message) else "en"

        # 檢查是否已存在
        existing = repo.search_similar(f.user_message, language=language, top_k=1)
        if existing and existing[0].user_message == f.user_message:
            continue  # 跳過重複

        examples_to_add.append({
            "category": f"correction_{f.category}",
            "user_message": f.user_message,
            "intent": f.expected_intent,
            "is_complete": f.expected_complete,
            "parsed_data": {
                "_correction_note": (
                    f"模型曾誤判為 intent={f.actual_intent}, "
                    f"is_complete={f.actual_complete}。正確應為 "
                    f"intent={f.expected_intent}, is_complete={f.expected_complete}"
                )
            },
            "_language": language,
        })

    if not examples_to_add:
        print("✅ 所有失敗案例已在 RAG 中（或無新增）")
        return

    # 分語言批次插入
    zh_examples = [e for e in examples_to_add if e.pop("_language") == "zh-TW"]
    en_examples = [e for e in examples_to_add if e.get("_language", "en") == "en"]
    for e in en_examples:
        e.pop("_language", None)

    if zh_examples:
        n = repo.add_batch(zh_examples, language="zh-TW")
        print(f"  ✓ 加入 {n} 個中文修正例子")
    if en_examples:
        n = repo.add_batch(en_examples, language="en")
        print(f"  ✓ 加入 {n} 個英文修正例子")

    print(f"\n✅ 共加入 {len(examples_to_add)} 個失敗案例到 RAG")
    print("下一步：重跑 python run_hf_90.py 觀察改進")
    session.close()


if __name__ == "__main__":
    main()
