"""
Embedding service — 使用 Google Gemini text-embedding-004 API（主要）+ HuggingFace API 備用。
不需要本地模型，無依賴衝突。
Gemini Free tier: 1500 requests/day, 100 req/min
HuggingFace Free tier: 1000 requests/hour
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
_HF_EMBED_URL = "https://api-inference.huggingface.co/models/BAAI/bge-base-zh-v1.5"
_EMBED_DIMS = 512


def _call_gemini_embed(text: str) -> List[float]:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    payload = json.dumps({
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


def _call_hf_embed(text: str) -> List[float]:
    """HuggingFace Inference API for bge-base-zh-v1.5 (768 dims, truncated to 512)."""
    api_key = os.getenv("HUGGINGFACE_API_KEY", "")
    if not api_key:
        raise RuntimeError("HUGGINGFACE_API_KEY not set")
    payload = json.dumps({"inputs": text or " "}).encode()
    req = urllib.request.Request(
        _HF_EMBED_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    # HF returns 768-dim vector, truncate to 512 to match schema
    if isinstance(result, list):
        return result[:_EMBED_DIMS]
    raise RuntimeError(f"Unexpected HF response: {result}")


class EmbeddingService:
    DIMS = _EMBED_DIMS

    @classmethod
    def embed(cls, text: str) -> List[float]:
        # Try Gemini first, fallback to HF
        try:
            arr = np.array(_call_gemini_embed(text), dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            return arr.tolist()
        except Exception as e:
            print(f"[Embedding] Gemini failed: {str(e)[:80]}, trying HF")
            try:
                arr = np.array(_call_hf_embed(text), dtype=np.float32)
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                return arr.tolist()
            except Exception as e2:
                print(f"[Embedding] HF also failed: {str(e2)[:80]}")
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
