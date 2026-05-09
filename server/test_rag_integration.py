"""Test RAG integration with AI service."""

import os
import json
from datetime import datetime, timezone, timedelta

from sqlmodel import Session
from app.db.database import engine
from app.repositories.rag_repository import RAGRepository
from app.services.rag_service import RAGService
from app.services.embedding_service import EmbeddingService
from app.services.ai_service import ai_service


def test_embedding_service():
    """Test that embedding service works."""
    print("\n📊 Testing Embedding Service...")
    try:
        embedding = EmbeddingService.embed("明天下午三點跟小明在星巴克吃飯")
        print(f"  ✓ Generated embedding with {len(embedding)} dimensions")
        assert len(embedding) == 512, f"Expected 512 dims, got {len(embedding)}"
        return True
    except Exception as e:
        print(f"  ✗ Embedding failed: {e}")
        return False


def test_rag_repository():
    """Test RAG repository operations."""
    print("\n📦 Testing RAG Repository...")
    session = Session(engine)
    try:
        repo = RAGRepository(session)

        # Test: Add example
        example = repo.add_example(
            language="zh-TW",
            category="test",
            user_message="明天下午三點跟小明吃飯",
            intent="create",
            is_complete=False,
            parsed_data={"title": "與小明吃飯"},
        )
        print(f"  ✓ Added example with ID: {example.id}")

        # Test: Search similar
        results = repo.search_similar(
            user_message="后天晚上六點跟文哥在信義吃飯",
            language="zh-TW",
            top_k=3,
        )
        print(f"  ✓ Found {len(results)} similar examples")

        # Test: Count
        count = repo.count_by_language("zh-TW")
        print(f"  ✓ Total zh-TW examples: {count}")

        return True
    except Exception as e:
        print(f"  ✗ Repository test failed: {e}")
        return False
    finally:
        session.close()


def test_rag_service():
    """Test RAG service formatting."""
    print("\n🔍 Testing RAG Service...")
    session = Session(engine)
    try:
        from app.services.rag_service import get_rag_service
        rag_svc = get_rag_service(session)

        # Check if RAG is available
        has_rag = rag_svc.should_use_rag("zh-TW")
        print(f"  ✓ RAG available: {has_rag}")

        if has_rag:
            # Get examples
            examples = rag_svc.get_relevant_examples(
                user_message="明天跟朋友吃飯",
                language="zh-TW",
                top_k=2,
            )
            print(f"  ✓ Retrieved {len(examples)} relevant examples")

            # Format for prompt
            formatted = rag_svc.format_examples_for_prompt(examples, "zh-TW")
            print(f"  ✓ Formatted for prompt ({len(formatted)} chars)")

        return True
    except Exception as e:
        print(f"  ✗ RAG service test failed: {e}")
        return False
    finally:
        session.close()


def test_ai_with_rag():
    """Test AI service with RAG integration."""
    print("\n🤖 Testing AI Service with RAG...")
    session = Session(engine)
    try:
        TAIPEI_TZ = timezone(timedelta(hours=8))
        today = datetime.now(tz=TAIPEI_TZ)

        result = ai_service.process_conversation(
            user_message="明天下午三點跟小明在星巴克吃飯",
            current_context={},
            conversation_history=[],
            schedule_list=[],
            session=session,
            language="zh-TW",
        )

        print(f"  ✓ AI processed message")
        print(f"    - Intent: {result.get('intent')}")
        print(f"    - Is complete: {result.get('is_complete')}")
        if result.get('reply'):
            print(f"    - Reply: {result['reply'][:50]}...")

        return True
    except Exception as e:
        print(f"  ✗ AI with RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()


def main():
    print("=" * 60)
    print("🧪 RAG Integration Test Suite")
    print("=" * 60)

    results = []

    results.append(("Embedding Service", test_embedding_service()))
    results.append(("RAG Repository", test_rag_repository()))
    results.append(("RAG Service", test_rag_service()))
    results.append(("AI with RAG", test_ai_with_rag()))

    print("\n" + "=" * 60)
    print("📋 Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! RAG is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check configuration.")
        return 1


if __name__ == "__main__":
    exit(main())
