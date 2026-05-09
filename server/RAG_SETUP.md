# RAG (Retrieval Augmented Generation) Setup Guide

## Overview

RAG enhances the AI assistant by injecting similar training examples into the system prompt, helping the model make better decisions about intent classification, data extraction, and multi-turn handling.

**Baseline Performance**: 51% (without RAG)  
**Target with RAG**: 70%+ (with improved contextual examples)

## Architecture

```
User Message
  ↓
[1. Query Embedding] → Convert user message to 768-dim vector (bge-base-zh-v1.5)
  ↓
[2. Vector Search] → Find 3-5 similar examples from RAG database (pgvector)
  ↓
[3. Format Examples] → Convert examples to readable format for prompt
  ↓
[4. Inject Prompt] → Add examples to system prompt section
  ↓
[5. AI Processing] → Model uses examples to improve response quality
```

## Components

### 1. Embedding Model: `bge-base-zh-v1.5`
- **Size**: 400MB download, 1GB RAM at runtime
- **Dimensions**: 768
- **Language**: Optimized for Chinese, works well for English too
- **Cost**: Free, runs locally or via HuggingFace API

### 2. Vector Database: PostgreSQL + pgvector
- **Table**: `rag_example`
- **Index**: HNSW (faster than IVFFlat, no pre-configuration needed)
- **Storage**: ~448 training examples (Chinese + English)

### 3. RAG Pipeline Components
- `embedding_service.py`: Embed texts to vectors (local or API fallback)
- `rag_example.py`: SQLModel for storing examples with embeddings
- `rag_repository.py`: Database operations (add, search, batch insert)
- `rag_service.py`: High-level RAG retrieval and formatting
- `populate_rag.py`: Script to populate database with training data

## Setup Steps

### Step 1: Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

This includes `sentence-transformers` which provides bge-base-zh-v1.5 model.

### Step 2: Run Database Migrations

```bash
python run_migration.py
```

This creates:
- `rag_example` table with pgvector columns
- HNSW index for fast vector search

### Step 3: Populate RAG Examples

```bash
python populate_rag.py
```

This loads training data from:
- `app/data/rag_training_data.py` (223 Chinese examples)
- `app/data/rag_training_data_en_v3.py` (87 English examples)

Expected output:
```
✓ Inserted 223 zh-TW examples
✓ Inserted 87 en examples
✅ Total 310 RAG examples inserted successfully
```

### Step 4: Test RAG Integration

```bash
python test_rag_integration.py
```

This runs:
1. Embedding service test (generate vectors)
2. RAG repository test (store/search examples)
3. RAG service test (format for prompt)
4. AI service test (end-to-end with RAG)

Expected output:
```
✅ PASS: Embedding Service
✅ PASS: RAG Repository
✅ PASS: RAG Service
✅ PASS: AI with RAG

🎉 All tests passed! RAG is ready to use.
```

## Configuration

### Environment Variables

```bash
# Choose embedding approach
EMBEDDING_USE_LOCAL=true          # Use local bge-base-zh-v1.5 (recommended, free)
# EMBEDDING_USE_LOCAL=false       # Use Gemini API (backup)

# For Gemini API fallback
GEMINI_API_KEY=...                # Required if using API

# Database
DATABASE_URL=postgresql://...     # Must have pgvector extension
```

### Model Selection

The embedding service automatically:
1. **Primary**: Use local bge-base-zh-v1.5 (if `EMBEDDING_USE_LOCAL=true`)
2. **Fallback**: Use Gemini text-embedding-004 API (if available)

To force local-only (no API fallback):
```python
# In rag_service.py
_use_local = True  # No fallback
```

## How RAG is Integrated

### In the Chat Flow

```python
# ai_service.py
def process_conversation(..., session=None, language="zh-TW"):
    # ... build context ...
    
    # Retrieve similar examples via RAG
    if session:
        rag_examples = rag_service.get_relevant_examples(
            user_message=user_message,
            language=language,
            top_k=3
        )
        rag_section = rag_service.format_examples_for_prompt(rag_examples)
    
    # Inject into system prompt
    system_prompt = build_system_prompt(
        ..., 
        rag_section=rag_section
    )
```

### Example Injection in Prompt

The system prompt now includes:

```
## 相似的成功案例（供參考）:

### 案例 1:
**用戶**: 明天下午三點跟小明在星巴克吃飯
**意圖**: create
**完整**: True
**提取結果**:
  - title: 與小明吃飯
  - start_time: 2026-05-10T15:00:00
  - location: 星巴克
  - participants: [@小明]
```

## Performance Metrics

### Embedding
- **Local (bge-base-zh-v1.5)**: ~100ms per request, 0 API costs
- **API (Gemini)**: ~200ms per request, free tier: 1500/day

### Vector Search
- **Query latency**: <10ms with HNSW index
- **Retrieval**: 3-5 most similar examples per request

### AI Improvement
- **Without RAG**: 51% pass rate on 90-test suite
- **With RAG**: Expected 70%+ (to be verified)

## Troubleshooting

### Issue: "sentence-transformers not installed"
```bash
pip install sentence-transformers
```

### Issue: HNSW index errors
Check that pgvector extension is installed:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: Slow vector search
- Verify HNSW index exists: `\d rag_example` in psql
- Check index stats: `SELECT COUNT(*) FROM rag_example;`

### Issue: Memory usage too high
The local model uses ~1GB RAM. If constrained:
1. Use API embedding instead: `EMBEDDING_USE_LOCAL=false`
2. Reduce HNSW `ef_construction` in migration (trades latency for memory)

## Advanced Usage

### Custom Example Scoring

To weight examples by category or intent:

```python
# In rag_service.py
def get_relevant_examples(..., intent=None):
    # Filter by intent for more relevant examples
    return self.repo.search_similar(
        user_message=user_message,
        intent=intent,  # e.g., "create", "edit"
        top_k=5
    )
```

### Batch Embedding Updates

To update embeddings after adding new examples:

```bash
python -c "
from app.db.database import SessionLocal
from app.repositories.rag_repository import RAGRepository

session = SessionLocal()
repo = RAGRepository(session)
# Examples are auto-embedded on add_batch()
"
```

### Monitor RAG Quality

Track how often RAG examples match the user's actual intent:

```python
# Log in ai_service.py
if examples:
    print(f"[RAG] Retrieved {len(examples)} examples, "
          f"top match intent={examples[0].intent}, "
          f"user intent={actual_intent}")
```

## Next Steps

1. **Run migrations**: `python run_migration.py`
2. **Populate data**: `python populate_rag.py`
3. **Test setup**: `python test_rag_integration.py`
4. **Run 90-test suite**: `python run_hf_90.py` to measure improvement
5. **Monitor quality**: Track RAG effectiveness over time

## Cost Savings

| Approach | Cost | Memory | Latency |
|----------|------|--------|---------|
| Local bge-base-zh | $0/month | 1GB | 100ms |
| Gemini API | $0/month (1500/day free) | Minimal | 200ms |
| OpenAI Embedding | $0.02/1K tokens | Minimal | 300ms |

**Recommendation**: Use local bge-base-zh-v1.5 with Gemini API as fallback.

## References

- [Sentence-Transformers Documentation](https://www.sbert.net/)
- [BGE Model Card](https://huggingface.co/BAAI/bge-base-zh-v1.5)
- [PGVector Documentation](https://github.com/pgvector/pgvector)
- [HNSW Index Paper](https://arxiv.org/abs/1802.02413)
