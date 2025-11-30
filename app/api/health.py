"""Health check API endpoints."""

from fastapi import APIRouter
from typing import Dict, Any
import logging

from ..services.glossary_service import GlossaryService
from ..services.query_executor import QueryExecutor
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["health"])

# Initialize services for health checks
glossary_service = GlossaryService()
query_executor = QueryExecutor()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "service": "bi-gpt",
        "version": "1.0.0"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check with service status."""
    health_status = {
        "status": "healthy",
        "service": "bi-gpt",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Check glossary service
    try:
        glossary = glossary_service.get_glossary()
        health_status["checks"]["glossary"] = {
            "status": "healthy",
            "version": glossary.version,
            "terms_count": len(glossary.terms),
            "tables_count": len(glossary.table_mappings)
        }
    except Exception as e:
        health_status["checks"]["glossary"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check database connection
    try:
        db_healthy = query_executor.test_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "connection": "ok" if db_healthy else "failed"
        }
        if not db_healthy:
            health_status["status"] = "unhealthy"
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Check OpenAI API (if configured)
    if settings.openai_api_key:
        try:
            # Simple check - in production, you might want to make a test call
            health_status["checks"]["openai"] = {
                "status": "configured",
                "model": settings.openai_model
            }
        except Exception as e:
            health_status["checks"]["openai"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_status["checks"]["openai"] = {
            "status": "not_configured"
        }
    
    return health_status


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get basic metrics."""
    try:
        glossary = glossary_service.get_glossary()
        
        return {
            "glossary_version": glossary.version,
            "business_terms_count": len(glossary.terms),
            "table_mappings_count": len(glossary.table_mappings),
            "pii_columns_count": len(glossary.get_pii_columns()),
            "permitted_tables_count": len(glossary.get_permitted_tables())
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return {
            "error": str(e)
        }