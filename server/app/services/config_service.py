"""
Config service — 從 DB 動態讀取閾值與旗標（取代寫死的 magic number）。

用法：
    from app.services.config_service import config_get
    threshold = config_get('semantic_router.confidence_threshold', default=0.45)

特點：
- 內存快取（避免每個請求都打 DB）
- TTL 60s 自動 refresh（讓 INSERT/UPDATE 不需重啟）
- DB 不可用時用 default fallback
"""
import json
import time
from typing import Any

from sqlmodel import Session, select
from ..db.database import engine
from ..models.app_config import AppConfig

_cache: dict[str, tuple[Any, float]] = {}  # {key: (parsed_value, fetched_at)}
_TTL_SEC = 60


def _parse_value(raw: str, value_type: str) -> Any:
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    if value_type == "bool":
        return raw.lower() in ("true", "1", "yes")
    if value_type == "json":
        return json.loads(raw)
    return raw  # str


def config_get(key: str, default: Any = None) -> Any:
    """從 DB 取得設定值；DB 沒有或失敗就回傳 default。"""
    # Cache hit
    if key in _cache:
        value, fetched_at = _cache[key]
        if time.time() - fetched_at < _TTL_SEC:
            return value

    try:
        session = Session(engine)
        row = session.exec(
            select(AppConfig).where(AppConfig.key == key)
        ).first()
        session.close()

        if not row:
            _cache[key] = (default, time.time())
            return default

        parsed = _parse_value(row.value, row.value_type)
        _cache[key] = (parsed, time.time())
        return parsed

    except Exception as e:
        print(f"[ConfigService] Failed to load {key}: {e}, using default")
        return default


def config_set(key: str, value: Any, value_type: str = "str", description: str = ""):
    """設定值（INSERT 或 UPDATE）。"""
    session = Session(engine)
    row = session.exec(select(AppConfig).where(AppConfig.key == key)).first()
    raw = json.dumps(value) if value_type == "json" else str(value)
    if row:
        row.value = raw
        row.value_type = value_type
        if description:
            row.description = description
        from datetime import datetime
        row.updated_at = datetime.utcnow()
    else:
        row = AppConfig(key=key, value=raw, value_type=value_type, description=description)
        session.add(row)
    session.commit()
    session.close()
    _cache.pop(key, None)  # 清快取


def config_reload():
    """清空快取，下次 get 強制從 DB 讀。"""
    _cache.clear()
