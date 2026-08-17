from sqlmodel import SQLModel, create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

postgres_user = os.getenv("POSTGRES_USER", "postgres")
postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
postgres_port = os.getenv("POSTGRES_PORT", "5432")
postgres_db = os.getenv("POSTGRES_DB", "schedule_management")
postgres_schema = os.getenv("POSTGRES_SCHEMA")
if not postgres_schema:
    postgres_schema = "public"

DATABASE_URL = f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"

# ── 連線層 timeout ────────────────────────────────────────────────────────────
# 沒有這些設定時，網路斷掉不會讓請求失敗 —— 它會無限期卡住。實測抓到過一次
# 單一請求掛 38 分鐘，而 server 端的 statement_timeout 是 2 分鐘卻沒觸發：
# 代表問題不是慢查詢，是 socket 對端已經死了而 client 完全不知道，一直等下去，
# 連帶佔住一個 worker。
#
# 所以真正救得到的是 TCP keepalive，不是 statement_timeout —— 後者由 server 端
# 執行，封包根本到不了 server 的時候它不會有任何作用。
# （順帶一提：我們走 Supabase pooler（PgBouncer, transaction mode），啟動參數
#   裡的 options 會被忽略，所以就算想在這裡設 statement_timeout 也設不進去。）
_connect_args = {
    # 實測冷啟連線要 5.3s（池子熱了之後是 0.35s），所以留到 10s。
    # 設 5s 會在正式環境誤殺第一個請求。
    "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
    "keepalives": 1,
    "keepalives_idle": int(os.getenv("DB_KEEPALIVES_IDLE", "30")),
    "keepalives_interval": int(os.getenv("DB_KEEPALIVES_INTERVAL", "10")),
    "keepalives_count": int(os.getenv("DB_KEEPALIVES_COUNT", "3")),
}

engine = create_engine(
    DATABASE_URL,
    # Remote Postgres closes idle connections; without pre_ping the first
    # request after an idle period gets a dead connection and 500s.
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args=_connect_args,
    execution_options={"schema_translate_map": {None: postgres_schema}}
)

def get_session():
    with Session(engine) as session:
        yield session
