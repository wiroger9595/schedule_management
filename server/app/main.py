from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.api import api_router
from .db.database import engine

app = FastAPI(title="Schedule Management API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    from .db.database import postgres_schema
    
    # Ensure the schema exists before creating tables
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{postgres_schema}";'))
        
    SQLModel.metadata.create_all(engine)

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Schedule Management API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
