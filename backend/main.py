import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from backend.config.settings import settings
from backend.database.session import init_db, SessionLocal
from backend.storage import get_storage_provider
from backend.api.router import api_router
from backend.repositories.category_repository import CategoryRepository
from backend.repositories.settings_repository import SettingsRepository
from backend.utils.logger import logger
from backend.utils.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} [Environment: {settings.APP_ENV}]...")
    # Initialize database tables
    init_db()

    # Seed default categories and settings
    with SessionLocal() as db:
        cat_repo = CategoryRepository(db)
        cat_repo.seed_defaults()
        settings_repo = SettingsRepository(db)
        settings_repo.get_or_create()

    # Initialize storage provider and probe health
    storage = get_storage_provider()
    storage.check_health()

    logger.info("Application startup completed successfully.")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="REST API for Smart Document Processing and Management System with auto-categorization and duplicate detection.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Structured Request/Response Logging Middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Don't clutter logs with static asset queries in normal runs
    if not request.url.path.startswith("/static"):
        logger.info(f"{request.method} {request.url.path} - {response.status_code} ({duration_ms}ms)")

    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    return response


# Global Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning(f"Application error on {request.method} {request.url.path}: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.method} {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload.",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while processing your request."
            }
        }
    )


# Mount API routers (both /api and /api/v1 for versioning compatibility)
app.include_router(api_router, prefix="/api")
app.include_router(api_router, prefix="/api/v1")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Silence browser favicon 404s."""
    return Response(status_code=204)


# Mount Frontend static files
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """Serve the frontend single-page dashboard at root."""
        return FileResponse(frontend_dir / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
