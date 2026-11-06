from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routers import chat, investigations


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # tables are small and stable; no migration tool needed for this scope
    yield


app = FastAPI(title="CauseTrace API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(investigations.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"ok": True, "llm": "mock" if settings.use_mock else settings.groq_model}
