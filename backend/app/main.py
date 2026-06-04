from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import asyncio
import platform

# Fix for Windows "Event loop is closed" error
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.utils.database import init_db
from app.models import *  # noqa: F401, F403 — ensures all models are registered
from app.routes import auth, chat, system

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await init_db()
    os.makedirs("uploads", exist_ok=True)
    print("SUCCESS: Flaw AI backend started - tables created")
    yield
    # Shutdown
    print("INFO: Flaw AI backend shutting down")


app = FastAPI(
    title="Flaw AI",
    description="Full-stack AI Assistant API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(system.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Flaw AI"}
