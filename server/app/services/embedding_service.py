"""
Embedding service — 多 provider cascade，按免費額度從多到少排序。
一個達到上限就自動切換到下一個。

免費額度排序（每日）：
  1. Jina AI         ~1B tokens/month ≈ 30M+/day（最多）
  2. Voyage AI       50M tokens/month ≈ 1.6M/day
  3. Cohere Trial    100 calls/min（trial 期內）
  4. Gemini          1500 req/day
  5. HuggingFace     ~1000 req/hour ≈ 24K/day（不穩）

只需要設定有 key 的 provider，沒設的自動跳過。
所有 provider 統一輸出 512 維（與既有 schema 相容）。
"""
from __future__ import annotations
import json
import os
import time
import urllib.request
from typing import List, Callable, Optional

import numpy as np

_EMBED_DIMS = 512

# 同 provider 失敗後 cooldown（從 app_config 讀，預設 300 秒）
_DEFAULT_FAILURE_COOLDOWN_SEC = 300

def _get_failure_cooldown() -> int:
    try:
        from .config_service import config_get
        return int(config_get("embedding.failure_cooldown_sec",
                              default=_DEFAULT_FAILURE_COOLDOWN_SEC))
    except Exception:
        return _DEFAULT_FAILURE_COOLDOWN_SEC

_provider_failed_until: dict[str, float] = {}


# ============================================================
# Provider 實作（每個都 normalize 到 512 維 + L2 normalize）
# ============================================================

def _normalize_to_512(values: list[float]) -> list[float]:
    arr = np.array(values, dtype=np.float32).flatten()
    # Pad with zeros if shorter, truncate if longer
    if len(arr) < _EMBED_DIMS:
        arr = np.pad(arr, (0, _EMBED_DIMS - len(arr)))
    else:
        arr = arr[:_EMBED_DIMS]
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def _call_jina(text: str) -> List[float]:
    """Jina AI - 30M+ tokens/day free. https://jina.ai"""
    api_key = os.getenv("JINA_API_KEY", "")
    if not api_key:
        raise RuntimeError("JINA_API_KEY not set")
    payload = json.dumps({
        "model": "jina-embeddings-v3",
        "task": "retrieval.query",
        "dimensions": _EMBED_DIMS,
        "input": [text or " "],
    }).encode()
    req = urllib.request.Request(
        "https://api.jina.ai/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "schedule-management/1.0",  # 避免 Cloudflare 1010
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    return _normalize_to_512(result["data"][0]["embedding"])


def _call_voyage(text: str) -> List[float]:
    """Voyage AI - 50M tokens/month free. https://voyageai.com"""
    api_key = os.getenv("VOYAGE_API_KEY", "")
    if not api_key:
        raise RuntimeError("VOYAGE_API_KEY not set")
    payload = json.dumps({
        "input": [text or " "],
        "model": "voyage-3-lite",  # 免費 tier 的小模型
    }).encode()
    req = urllib.request.Request(
        "https://api.voyageai.com/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    return _normalize_to_512(result["data"][0]["embedding"])


def _call_cohere(text: str) -> List[float]:
    """Cohere Trial - 100 calls/min（trial 期間）。https://cohere.com"""
    api_key = os.getenv("COHERE_API_KEY", "")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY not set")
    payload = json.dumps({
        "texts": [text or " "],
        "model": "embed-multilingual-light-v3.0",
        "input_type": "search_query",
    }).encode()
    req = urllib.request.Request(
        "https://api.cohere.com/v1/embed",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    return _normalize_to_512(result["embeddings"][0])


def _call_gemini(text: str) -> List[float]:
    """Gemini gemini-embedding-001 - 1500/day. https://aistudio.google.com
    text-embedding-004 已棄用（404）。新模型輸出 3072 維，自動截斷。"""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    payload = json.dumps({
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": text or " "}]},
    }).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={api_key}",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
    return _normalize_to_512(result["embedding"]["values"])


_hf_client = None
def _call_hf(text: str) -> List[float]:
    """HuggingFace - ~1000/hour. https://huggingface.co"""
    global _hf_client
    api_key = os.getenv("HUGGINGFACE_API_KEY", "")
    if not api_key:
        raise RuntimeError("HUGGINGFACE_API_KEY not set")

    import socket
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(8.0)
    try:
        if _hf_client is None:
            from huggingface_hub import InferenceClient
            _hf_client = InferenceClient(api_key=api_key)
        result = _hf_client.feature_extraction(
            text or " ", model="BAAI/bge-base-zh-v1.5"
        )
    finally:
        socket.setdefaulttimeout(old_timeout)
    return _normalize_to_512(np.array(result).flatten().tolist())


# ============================================================
# Provider cascade（按免費額度從多到少）
# ============================================================

PROVIDERS = [
    # (name, env_key, daily_quota_label, function)
    ("jina",     "JINA_API_KEY",        "~30M tokens/day",  _call_jina),
    ("voyage",   "VOYAGE_API_KEY",      "~1.6M tokens/day", _call_voyage),
    ("cohere",   "COHERE_API_KEY",      "~144K req/day",    _call_cohere),
    ("gemini",   "GEMINI_API_KEY",      "1500 req/day",     _call_gemini),
    ("hf",       "HUGGINGFACE_API_KEY", "~24K req/day",     _call_hf),
]


def _is_in_cooldown(name: str) -> bool:
    until = _provider_failed_until.get(name, 0)
    return time.time() < until


def _mark_failed(name: str, error: Exception):
    """達到限流的錯誤碼 → 進入 cooldown；其他錯誤短暫跳過。"""
    s = str(error)
    if any(k in s for k in ("402", "429", "rate limit", "Payment Required",
                             "quota", "exhausted", "too many")):
        cooldown = _get_failure_cooldown()
        _provider_failed_until[name] = time.time() + cooldown
        print(f"[Embedding] {name} rate-limited, cooldown {cooldown}s")
    elif any(k in s for k in ("400", "401", "API key", "invalid", "expired")):
        # Key 問題 → 整個 session 跳過
        _provider_failed_until[name] = time.time() + 86400  # 24h
        print(f"[Embedding] {name} auth failed, skipping for 24h")
    else:
        _provider_failed_until[name] = time.time() + 60  # 短暫 1 分鐘


def _get_active_providers() -> list[tuple]:
    """回傳目前有設定 key 且未在 cooldown 的 provider 列表。"""
    active = []
    for name, env_key, quota, func in PROVIDERS:
        if not os.getenv(env_key):
            continue
        if _is_in_cooldown(name):
            continue
        active.append((name, quota, func))
    return active


def _print_cascade_once():
    """啟動時印出 cascade 順序（只印一次）。"""
    if getattr(_print_cascade_once, "_printed", False):
        return
    _print_cascade_once._printed = True
    active = []
    skipped = []
    for name, env_key, quota, _ in PROVIDERS:
        if os.getenv(env_key):
            active.append(f"{name} ({quota})")
        else:
            skipped.append(name)
    print(f"[Embedding] Cascade: {' → '.join(active) if active else 'NO PROVIDERS!'}")
    if skipped:
        print(f"[Embedding] Skipped (no API key): {', '.join(skipped)}")


# ============================================================
# 公開 API
# ============================================================

class EmbeddingService:
    DIMS = _EMBED_DIMS

    @classmethod
    def embed(cls, text: str) -> List[float]:
        _print_cascade_once()
        active = _get_active_providers()
        if not active:
            raise RuntimeError(
                "No embedding provider available. Set at least one API key: "
                + ", ".join(p[1] for p in PROVIDERS)
            )

        last_error = None
        for name, quota, func in active:
            try:
                return func(text)
            except Exception as e:
                last_error = e
                print(f"[Embedding] {name} failed: {str(e)[:80]}")
                _mark_failed(name, e)
                continue
        raise RuntimeError(f"All providers failed. Last error: {last_error}")

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

    @classmethod
    def status(cls) -> dict:
        """回傳目前 cascade 狀態（debug 用）。"""
        out = {}
        for name, env_key, quota, _ in PROVIDERS:
            has_key = bool(os.getenv(env_key))
            cooldown_until = _provider_failed_until.get(name, 0)
            out[name] = {
                "has_key": has_key,
                "quota": quota,
                "in_cooldown": time.time() < cooldown_until,
                "cooldown_remaining_sec": max(0, int(cooldown_until - time.time())),
            }
        return out


embedding_service = EmbeddingService()
