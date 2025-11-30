"""Metrics API endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging

from ..core.metrics import metrics_collector
from ..core.logging import query_logger, audit_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/overall")
async def get_overall_metrics() -> Dict[str, Any]:
    """Get overall system metrics."""
    try:
        return metrics_collector.get_overall_metrics()
    except Exception as e:
        logger.error(f"Failed to get overall metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/user/{user_id}")
async def get_user_metrics(user_id: str) -> Dict[str, Any]:
    """Get metrics for specific user."""
    try:
        return metrics_collector.get_user_metrics(user_id)
    except Exception as e:
        logger.error(f"Failed to get user metrics for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user metrics")


@router.get("/hourly")
async def get_hourly_stats(hours: int = 24) -> List[Dict[str, Any]]:
    """Get hourly statistics."""
    try:
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(status_code=400, detail="Hours must be between 1 and 168")
        
        return metrics_collector.get_hourly_stats(hours)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get hourly stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve hourly statistics")


@router.get("/recent")
async def get_recent_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent queries."""
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        
        return metrics_collector.get_recent_queries(limit)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recent queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent queries")


@router.get("/security")
async def get_security_metrics() -> Dict[str, Any]:
    """Get security-related metrics."""
    try:
        return metrics_collector.get_security_metrics()
    except Exception as e:
        logger.error(f"Failed to get security metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve security metrics")


@router.get("/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics."""
    try:
        return metrics_collector.get_performance_metrics()
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance metrics")


@router.get("/dashboard")
async def get_dashboard_metrics() -> Dict[str, Any]:
    """Get comprehensive dashboard metrics."""
    try:
        return {
            "overall": metrics_collector.get_overall_metrics(),
            "security": metrics_collector.get_security_metrics(),
            "performance": metrics_collector.get_performance_metrics(),
            "recent_queries": metrics_collector.get_recent_queries(5),
            "hourly_stats": metrics_collector.get_hourly_stats(24)
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard metrics")