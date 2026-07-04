"""
集中 logging 設定。main.py 啟動時呼叫 setup_logging()。

用法（各模組）：
    import logging
    logger = logging.getLogger(__name__)
    logger.info("...")

Log level 由環境變數 LOG_LEVEL 控制（DEBUG/INFO/WARNING/ERROR），預設 INFO。
"""
import logging
import os
import sys


def setup_logging() -> None:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    # 避免 uvicorn reload 時重複掛 handler
    if root.handlers:
        for h in root.handlers:
            root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(handler)
    root.setLevel(level)

    # 降噪：第三方套件只留 WARNING 以上
    for noisy in ("httpx", "httpcore", "urllib3", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
