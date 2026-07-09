from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.api import api_router
from .core.logging_config import setup_logging
from .db.database import engine

setup_logging()

app = FastAPI(title="Schedule Management API")

# CORS middleware
origins = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dashboard dev server
    "http://localhost:8080",
    "https://schedule-management-mu.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⚠️ TODO(security, 上線前必修):
#   此 middleware 無條件印出所有請求路徑，prod 上是雜訊也可能洩漏資訊。
#   上線前改用 logger.debug + env 開關（例如 DEBUG_REQUESTS=1 才開）。
from fastapi import Request
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: API Call - {request.method} {request.url.path}")
    response = await call_next(request)
    return response

@app.on_event("startup")
def on_startup():
    from sqlmodel import SQLModel, text
    # Import models so metadata is populated
    from .models.user import User
    from .models.schedule import Schedule
    from .models.contact import Contact
    from .models.attend import attend
    from .models.comment import Comment
    from .models.ai_feedback import AIFeedback
    from .models.ai_test_result import AITestResult
    from .models.app_config import AppConfig
    from .models.inference_default import InferenceDefault
    from .models.intent_anchor import IntentAnchor
    from .models.lexicon import Lexicon
    from .models.prompt_rule import PromptRule
    from .models.rag_example import RAGExample
    from .models.user_device import UserDevice  # Multi-device FCM support
    from .db.database import postgres_schema

    # Ensure the schema exists before creating tables
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{postgres_schema}";'))

    SQLModel.metadata.create_all(engine)

    # Initialize reminder scheduler (departure reminders for all schedules)
    from .services.background_reminder_scheduler import init_reminder_scheduler
    init_reminder_scheduler()
    print("[Startup] Reminder scheduler initialized")

@app.on_event("shutdown")
def on_shutdown():
    """Shutdown background services (reminder scheduler, etc.)"""
    from .services.background_reminder_scheduler import get_reminder_scheduler
    scheduler = get_reminder_scheduler()
    if scheduler:
        scheduler.shutdown()
        print("[Shutdown] Reminder scheduler shut down")


app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Schedule Management API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7800)
