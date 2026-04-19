"""
Embedding service — 使用 fastembed（ONNX runtime，不需要 PyTorch）。
Python 3.13 相容。

模型：BAAI/bge-small-zh-v1.5（中文優化，512 維，~90MB）
第一次啟動時自動下載模型快取，之後直接讀取。
"""
from __future__ import annotations
from typing import List, Optional
import numpy as np


class EmbeddingService:
    _model = None  # lazy-load singleton
    MODEL_NAME = "BAAI/bge-small-zh-v1.5"
    DIMS = 512

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            import os
            os.environ.setdefault("FASTEMBED_CACHE_PATH", "/app/.fastembed_cache")
            from fastembed import TextEmbedding
            print(f"[EmbeddingService] Loading model {cls.MODEL_NAME} ...")
            cls._model = TextEmbedding(model_name=cls.MODEL_NAME)
            print("[EmbeddingService] Model loaded.")
        return cls._model

    @classmethod
    def embed(cls, text: str) -> List[float]:
        """將文字轉為正規化向量"""
        model = cls._get_model()
        vec = next(model.embed([text]))
        arr = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    @classmethod
    def embed_batch(cls, texts: List[str]) -> List[List[float]]:
        """批次 embed，效率比逐筆高"""
        model = cls._get_model()
        results = []
        for vec in model.embed(texts):
            arr = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            results.append(arr.tolist())
        return results

    @classmethod
    def embed_schedule(cls, title: str, location: str = "",
                       description: str = "", contact_name: str = "",
                       start_time=None) -> List[float]:
        """
        將行程關鍵欄位合併後 embed。
        加入聯絡人姓名與時間語境，讓「與文哥見面」可被「文哥那個行程」找到。
        """
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
                # 加入星期 + 時段語境，讓時間語意搜尋有效
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
        """將聯絡人資訊 embed，用於語意人名搜尋"""
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
    def rerank_schedules(cls, query: str, schedules: list,
                         top_k: int = 10) -> list:
        """對已有 embedding 的行程列表做本地重排序"""
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
