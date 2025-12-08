"""
EMO Backend - FastAPI Application
=================================
RESTful API for EMO AI Assistant with LangGraph agent.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from routers import chat, auth, email, calendar, tasks

# Import database
from database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print("🚀 EMO Backend starting...")
    
    # Initialize database
    try:
        init_db()
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
    
    yield
    
    # Cleanup
    print("👋 EMO Backend shutting down...")
    try:
        close_db()
    except Exception as e:
        print(f"⚠️ Database cleanup error: {e}")


# Create FastAPI app
app = FastAPI(
    title="EMO API",
    description="AI Personal Assistant with Gmail, Calendar, and Memory integration",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://127.0.0.1:3000",
        "https://*.vercel.app",   # Vercel deployments
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(email.router, tags=["Email"])  # Direct email fetch
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(tasks.router, prefix="/api", tags=["Tasks"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "EMO Backend",
        "version": "2.0.0",
    }


@app.get("/api/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY")),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
