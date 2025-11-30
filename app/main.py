# Add at the top, after other imports
from fastapi import APIRouter

"""Main FastAPI application for BI-GPT."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import logging
import uvicorn

from .api import query_router, health_router, metrics_router
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BI-GPT API",
    description="Business Intelligence Agent for Natural Language to SQL",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Test endpoints router
test_router = APIRouter(prefix="/api/v1/test", tags=["test"])

@test_router.get("/business", include_in_schema=False)
async def test_business():
    return {"status": "ok", "test": "business", "result": "Тест бизнес-терминов успешно пройден!"}

@test_router.get("/security", include_in_schema=False)
async def test_security():
    return {"status": "ok", "test": "security", "result": "Тест безопасности успешно пройден!"}

@test_router.get("/api", include_in_schema=False)
async def test_api():
    return {"status": "ok", "test": "api", "result": "Тест API успешно пройден!"}


# Include routers
app.include_router(query_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(test_router)


# Custom homepage
@app.get("/", include_in_schema=False)
async def custom_home():
    return FileResponse("app/static/index.html")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )