"""FastAPI application entrypoint for LLMOps Studio."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.core.security import sanitize_error_message
from app.db.session import async_session_factory, init_db
from app.providers.registry import provider_registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Initializing LLMOps Studio database and default registry...")
    await init_db()

    async with async_session_factory() as session:
        await provider_registry.seed_defaults(session)

    logger.info("LLMOps Studio ready to serve.")
    yield
    logger.info("Shutting down LLMOps Studio...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LLM Evaluation, Experimentation & Observability Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Sanitize uncaught server exceptions to prevent credential or stack leakages."""
    safe_msg = sanitize_error_message(exc)
    logger.error(f"Uncaught server exception on {request.url.path}: {safe_msg}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred.", "message": safe_msg},
    )


# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve Frontend static assets
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """Serve main frontend single-page dashboard."""
        index_file = frontend_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "LLMOps Studio API operational. Frontend not found."}

