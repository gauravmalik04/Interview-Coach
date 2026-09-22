import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import init_db, close_db
from backend.services.question_loader import question_loader
from backend.routers import auth, sessions, reports, coach
from backend.ws import interview_ws
from fastapi.responses import FileResponse, HTMLResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("ai_interview.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown hooks."""
    logger.info("Starting AI Interview Platform backend...")
    
    # 1. Initialize SQLite Database & Tables
    await init_db()
    
    # 2. Pre-load question bank
    await question_loader.load_questions()
    logger.info(f"Question bank initialized with {len(question_loader.get_all_questions())} technical questions.")
    
    yield
    
    # Clean up database connections on shutdown
    await close_db()
    logger.info("AI Interview Platform backend shut down cleanly.")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Full-stack AI Interview Platform powered by LangGraph, Hugging Face, and ChromaDB",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(reports.router)
app.include_router(coach.router)
app.include_router(interview_ws.router)

# Health check route
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "questions_loaded": len(question_loader.get_all_questions()),
    }

# Mount Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    def _safe_serve(file_name: str):
        target = FRONTEND_DIR / file_name
        if target.exists():
            return FileResponse(target)
        return HTMLResponse(
            f"<!DOCTYPE html><html><head><title>GAIUS — Coming Soon</title><link rel='stylesheet' href='/static/css/main.css'></head>"
            f"<body style='display:flex;align-items:center;justify-content:center;height:100vh;flex-direction:column;text-align:center;padding:2rem;'>"
            f"<h1 style='font-size:2rem;margin-bottom:1rem;'>Under Active Preparation</h1>"
            f"<p style='color:var(--text-secondary);margin-bottom:1.5rem;'>The requested view (<code>{file_name}</code>) is being finalized.</p>"
            f"<a href='/dashboard' class='btn btn-primary'>← Return to Dashboard</a></body></html>",
            status_code=200
        )

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return _safe_serve("index.html")

    @app.get("/dashboard", include_in_schema=False)
    async def serve_dashboard():
        return _safe_serve("dashboard.html")

    @app.get("/interview", include_in_schema=False)
    async def serve_interview():
        return _safe_serve("interview.html")

    @app.get("/report", include_in_schema=False)
    async def serve_report():
        return _safe_serve("report.html")

    @app.get("/coach", include_in_schema=False)
    async def serve_coach():
        return _safe_serve("coach.html")

    @app.get("/history", include_in_schema=False)
    async def serve_history():
        return _safe_serve("history.html")

