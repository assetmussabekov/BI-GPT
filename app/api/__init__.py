"""API package for BI-GPT application."""

from .query import router as query_router
from .health import router as health_router
from .metrics import router as metrics_router

__all__ = ["query_router", "health_router", "metrics_router"]