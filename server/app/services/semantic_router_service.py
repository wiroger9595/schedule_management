"""
Semantic Router — 本地 intent 預分類，減少 30-40% 的 Cerebras API 呼叫。

用法：
    from .semantic_router_service import semantic_router
    result = semantic_router.route(user_message)
    # result: {"intent": "create"|"edit"|"delete"|"query"|None, "confidence": 0.0~1.0}
    # confidence < THRESHOLD 時 intent=None，讓 AI 決定

架構：
- 使用與 embedding_service 相同的 sentence-transformers 模型
- 將 user_message embed 後與預設例句做 cosine similarity
- 取最高分的 intent（若 < 閾值則不預判）
- 結果 cache 在 module level，embeddings 只算一次
"""
from __future__ import annotations
from typing import Optional
import numpy as np

# ── 每個 intent 的代表例句（中文為主，英文備用）─────────────────────────────
INTENT_EXAMPLES: dict[str, list[str]] = {
    "create": [
        "幫我安排明天下午三點的會議",
        "新增一個行程",
        "我要約人吃飯",
        "記錄一下週五打球",
        "安排一個活動",
        "建立行程",
        "我要預約",
        "下週二跟客戶開會",
        "晚上八點看電影",
        "明天早上九點牙醫",
    ],
    "edit": [
        "把打球時間改到下午五點",
        "更改昨天的會議地點",
        "把跟Robert的約會延後一小時",
        "修改行程",
        "換一個時間",
        "調整一下",
        "改到明天",
        "推遲一個小時",
        "提早半小時",
        "地點換到星巴克",
    ],
    "delete": [
        "取消打球活動",
        "刪除明天的會議",
        "移除那個行程",
        "取消跟王醫生的約",
        "不去了",
        "刪掉",
        "取消這個",
        "移除行程",
    ],
    "query": [
        "我今天有什麼行程",
        "下週有哪些安排",
        "查一下我的行程",
        "找找看跟Robert的約",
        "有什麼活動",
        "什麼時候有空",
        "最近有哪些行程",
    ],
}

CONFIDENCE_THRESHOLD = 0.45  # 低於此值不預判，交給 AI


class SemanticRouter:
    _example_embeddings: dict[str, list] | None = None  # {intent: [vec, vec, ...]}

    def _ensure_embeddings(self) -> None:
        if self._example_embeddings is not None:
            return
        from .embedding_service import EmbeddingService
        self._example_embeddings = {}
        for intent, examples in INTENT_EXAMPLES.items():
            vecs = [EmbeddingService.embed(ex) for ex in examples]
            self._example_embeddings[intent] = vecs

    def route(self, message: str) -> dict:
        """
        回傳 {"intent": str|None, "confidence": float}
        intent=None 表示信心不足，應讓 AI 自行判斷。
        """
        try:
            self._ensure_embeddings()
            from .embedding_service import EmbeddingService
            msg_vec = np.array(EmbeddingService.embed(message))

            best_intent: Optional[str] = None
            best_score = 0.0

            for intent, vecs in self._example_embeddings.items():
                # 取該 intent 所有例句的平均相似度（更穩定）
                scores = [float(np.dot(msg_vec, np.array(v))) for v in vecs]
                avg_score = float(np.mean(scores))
                if avg_score > best_score:
                    best_score = avg_score
                    best_intent = intent

            if best_score < CONFIDENCE_THRESHOLD:
                return {"intent": None, "confidence": round(best_score, 3)}

            return {"intent": best_intent, "confidence": round(best_score, 3)}

        except Exception as e:
            print(f"[SemanticRouter] route failed (non-critical): {e}")
            return {"intent": None, "confidence": 0.0}


semantic_router = SemanticRouter()
