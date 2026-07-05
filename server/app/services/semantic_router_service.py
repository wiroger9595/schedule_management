"""
Semantic Router — 從 DB 載入 intent 錨點，替代硬編碼 INTENT_EXAMPLES。

用法：
    from .semantic_router_service import semantic_router
    result = semantic_router.route(user_message)
    # result: {"intent": "create"|"edit"|"delete"|"query"|None, "confidence": 0.0~1.0}

新加 intent 例句的方式：
    INSERT INTO intent_anchor (intent, example, language) VALUES (...);
    然後重啟 server（或呼叫 semantic_router.reload()）

如果 DB 沒資料，會 fallback 到舊的硬編碼 INTENT_EXAMPLES 確保服務不中斷。
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import logging
logger = logging.getLogger(__name__)

# ── Fallback 例句（DB 為空或載入失敗時使用，避免服務中斷）────────────────────
_FALLBACK_INTENT_EXAMPLES: dict[str, list[str]] = {
    "create": ["幫我安排明天下午三點的會議", "新增一個行程"],
    "edit":   ["把打球時間改到下午五點", "修改行程"],
    "delete": ["取消打球活動", "刪除明天的會議"],
    "query":  ["我今天有什麼行程", "查一下我的行程"],
}

_DEFAULT_CONFIDENCE_THRESHOLD = 0.45  # fallback；實際從 app_config 讀

def _get_threshold():
    try:
        from .config_service import config_get
        return config_get("semantic_router.confidence_threshold",
                          default=_DEFAULT_CONFIDENCE_THRESHOLD)
    except Exception:
        return _DEFAULT_CONFIDENCE_THRESHOLD


class SemanticRouter:
    _intent_data: dict[str, list] | None = None  # {intent: [{"example", "embedding"}, ...]}
    _used_fallback: bool = False

    def reload(self) -> None:
        """Force reload from DB. Call after adding new anchors via SQL."""
        self._intent_data = None
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if self._intent_data is not None:
            return

        # 嘗試從 DB 載入
        try:
            from ..db.database import engine
            from sqlmodel import Session
            from ..repositories.intent_anchor_repository import IntentAnchorRepository

            session = Session(engine)
            repo = IntentAnchorRepository(session)
            data = repo.get_all_by_language(language="zh-TW")
            session.close()

            if data and any(data.values()):
                self._intent_data = data
                total = sum(len(v) for v in data.values())
                logger.info(f"[SemanticRouter] Loaded {total} anchors from DB")
                return
            else:
                logger.info("[SemanticRouter] DB has no anchors, using fallback")
        except Exception as e:
            logger.info(f"[SemanticRouter] DB load failed: {e}, using fallback")

        # Fallback 到硬編碼例句
        self._used_fallback = True
        from .embedding_service import EmbeddingService
        self._intent_data = {}
        for intent, examples in _FALLBACK_INTENT_EXAMPLES.items():
            embeddings = EmbeddingService.embed_batch(examples)
            self._intent_data[intent] = [
                {"example": ex, "embedding": emb}
                for ex, emb in zip(examples, embeddings)
            ]

    def route(self, message: str, query_embedding: list | None = None) -> dict:
        """
        回傳 {"intent": str|None, "confidence": float}
        intent=None 表示信心不足，應讓 AI 自行判斷。
        query_embedding: 呼叫端已算好的 embedding，傳入可省一次 API 呼叫。
        """
        try:
            self._ensure_loaded()
            if query_embedding is not None:
                msg_vec = np.array(query_embedding)
            else:
                from .embedding_service import EmbeddingService
                msg_vec = np.array(EmbeddingService.embed(message))

            best_intent: Optional[str] = None
            best_score = 0.0

            for intent, items in self._intent_data.items():
                # 取該 intent 最相似的前 3 條例句平均：全例句平均會被多樣化
                # 錨點稀釋（原句比對也只剩 0.35~0.6，永遠過不了門檻），
                # 純 max 又容易被單一離群錨點帶偏。
                scores = sorted(
                    (float(np.dot(msg_vec, np.array(it["embedding"]))) for it in items),
                    reverse=True,
                )
                top_score = float(np.mean(scores[:3]))
                if top_score > best_score:
                    best_score = top_score
                    best_intent = intent

            if best_score < _get_threshold():
                return {"intent": None, "confidence": round(best_score, 3)}

            return {"intent": best_intent, "confidence": round(best_score, 3)}

        except Exception as e:
            logger.info(f"[SemanticRouter] route failed (non-critical): {e}")
            return {"intent": None, "confidence": 0.0}


semantic_router = SemanticRouter()

# Eager-load at module import so first request doesn't pay the cost
try:
    semantic_router._ensure_loaded()
except Exception as _err:
    logger.info(f"[SemanticRouter] Eager load skipped (non-critical): {_err}")
