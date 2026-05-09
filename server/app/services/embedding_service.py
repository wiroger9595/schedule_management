"""
Embedding service — 使用 HuggingFace Inference API（主要）+ Gemini API 備用。
不需要本地模型，無依賴衝突。
HuggingFace bge-base-zh-v1.5: 免費，768 維（截斷至 512）
Gemini text-embedding-004: 1500/day（如果有效 key）
輸出 512 維（與現有 pgvector schema 相容）。
"""
from __future__ import annotations
import json
import os
import urllib.request
from typing import List

import numpy as np

_GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "text-embedding-004:embedContent"
)
_HF_MODEL = "BAAI/bge-base-zh-v1.5"
_EMBED_DIMS = 512

# Lazy-loaded HF client
_hf_client = None


def _get_hf_client():
    global _hf_client
    if _hf_client is None:
        from huggingface_hub import InferenceClient
        api_key = os.getenv("HUGGINGFACE_API_KEY", "")
        if not api_key:
            raise RuntimeError("HUGGINGFACE_API_KEY not set")
        _hf_client = InferenceClient(api_key=api_key)
    return _hf_client


def _call_hf_embed(text: str) -> List[float]:
    """HuggingFace Inference API for bge-base-zh-v1.5 (768 dims, truncated to 512)."""
    client = _get_hf_client()
    result = client.feature_extraction(text or " ", model=_HF_MODEL)
    # Returns numpy array of shape (768,)
    arr = np.array(result, dtype=np.float32).flatten()
    # Truncate 768 → 512
    arr = arr[:_EMBED_DIMS]
    # Normalize
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def _call_gemini_embed(text: str) -> List[float]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    payload = json.dumps({
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text or " "}]},
        "outputDimensionality": _EMBED_DIMS,
    }).encode()
    req = urllib.request.Request(
        f"{_GEMINI_EMBED_URL}?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    return result["embedding"]["values"]


class EmbeddingService:
    DIMS = _EMBED_DIMS

    @classmethod
    def embed(cls, text: str) -> List[float]:
        # Try HF first (Gemini key may be expired), fallback to Gemini
        try:
            return _call_hf_embed(text)
        except Exception as e:
            print(f"[Embedding] HF failed: {str(e)[:80]}, trying Gemini")
            try:
                arr = np.array(_call_gemini_embed(text), dtype=np.float32)
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                return arr.tolist()
            except Exception as e2:
                print(f"[Embedding] Gemini also failed: {str(e2)[:80]}")
                raise

    @classmethod
    def embed_batch(cls, texts: List[str]) -> List[List[float]]:
        return [cls.embed(t) for t in texts]

    @classmethod
    def embed_schedule(cls, title: str, location: str = "",
                       description: str = "", contact_name: str = "",
                       start_time=None) -> List[float]:
        parts = []
        if title:
            parts.append(title)
        if contact_name:
            parts.append(f"與{contact_name}")
        if location:
            parts.append(f"地點{location}")
        if start_time:
            try:
                import arrow as _arrow
                t = _arrow.get(start_time).to("Asia/Taipei")
                hour = t.hour
                if 6 <= hour < 12:
                    period = "上午"
                elif 12 <= hour < 14:
                    period = "中午"
                elif 14 <= hour < 18:
                    period = "下午"
                elif 18 <= hour < 22:
                    period = "晚上"
                else:
                    period = "深夜"
                parts.append(f"{t.format('dddd')} {period}{hour}點")
            except Exception:
                pass
        if description:
            parts.append(description)
        text = " ".join(p.strip() for p in parts if p and p.strip())
        return cls.embed(text if text else (title or "未命名"))

    @classmethod
    def embed_contact(cls, nick_name: str, comment: str = "") -> List[float]:
        parts = [nick_name] if nick_name else []
        if comment:
            parts.append(comment)
        text = " ".join(parts)
        return cls.embed(text if text else "unknown")

    @classmethod
    def cosine_similarity(cls, a: List[float], b: List[float]) -> float:
        va, vb = np.array(a), np.array(b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)

    @classmethod
    def rerank_schedules(cls, query: str, schedules: list, top_k: int = 10) -> list:
        if not schedules:
            return []
        query_vec = cls.embed(query)
        scored = []
        for s in schedules:
            emb = s.get("embedding")
            score = cls.cosine_similarity(query_vec, emb) if emb else 0.0
            s_copy = dict(s)
            s_copy["_similarity"] = round(score, 4)
            scored.append((score, s_copy))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]


embedding_service = EmbeddingService()
