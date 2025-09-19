from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import asyncio
from .api.routes import router
from .api.rfp_routes import router as rfp_router
from .core.config import get_settings
from .middleware.error_handler import error_handler_middleware, handle_exception
from .core.errors import AppError
from .services.rfp_daemon import get_daemon

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="A comprehensive App Garden template with advanced features for building AI-powered applications",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add global error handling middleware
@app.middleware("http")
async def add_error_handling(request: Request, call_next):
    return await error_handler_middleware(request, call_next)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return handle_exception(exc, getattr(request.state, 'request_id', 'unknown'))

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return handle_exception(exc, getattr(request.state, 'request_id', 'unknown'))

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return handle_exception(exc, getattr(request.state, 'request_id', 'unknown'))

# Include API routes
app.include_router(router, prefix="/api")
app.include_router(rfp_router)  # RFP routes already have /api/rfp prefix


@app.on_event("startup")
async def startup_event():
    """Start the RFP daemon on application startup"""
    try:
        daemon = get_daemon()
        asyncio.create_task(daemon.start())
        logging.info("RFP Discovery Daemon started")
    except Exception as e:
        logging.error(f"Failed to start RFP daemon: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop the RFP daemon on application shutdown"""
    try:
        daemon = get_daemon()
        await daemon.stop()
        logging.info("RFP Discovery Daemon stopped")
    except Exception as e:
        logging.error(f"Error stopping RFP daemon: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    daemon = get_daemon()
    daemon_status = "running" if daemon.is_running else "stopped"

    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "rfp_daemon": daemon_status
    }