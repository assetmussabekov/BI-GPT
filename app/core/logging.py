"""Logging configuration for BI-GPT."""

import logging
from typing import Any, Dict
import json
from datetime import datetime

# Optional structlog import for demo mode
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    structlog = None

from ..config import settings


def setup_logging() -> None:
    """Setup structured logging for the application."""
    
    # Configure structlog if available
    if STRUCTLOG_AVAILABLE:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )


class QueryLogger:
    """Structured logger for query operations."""
    
    def __init__(self):
        if STRUCTLOG_AVAILABLE:
            self.logger = structlog.get_logger("query")
        else:
            self.logger = logging.getLogger("query")
    
    def log_query_start(self, request_id: str, user_id: str, question: str) -> None:
        """Log query start."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info(
                "query_started",
                request_id=request_id,
                user_id=user_id,
                question=question[:200] + "..." if len(question) > 200 else question
            )
        else:
            self.logger.info(f"Query started: {request_id} by {user_id}: {question[:100]}...")
    
    def log_sql_generated(self, request_id: str, sql: str, confidence: float) -> None:
        """Log SQL generation."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info("sql_generated", request_id=request_id, sql=sql, confidence=confidence)
        else:
            self.logger.info(f"SQL generated: {request_id} (confidence: {confidence:.2f})")
    
    def log_security_check(self, request_id: str, security_level: str, is_safe: bool, warnings: list) -> None:
        """Log security check results."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info("security_check", request_id=request_id, security_level=security_level, is_safe=is_safe, warnings=warnings)
        else:
            self.logger.info(f"Security check: {request_id} - {security_level} - Safe: {is_safe}")
    
    def log_query_execution(self, request_id: str, execution_time_ms: float, row_count: int, success: bool) -> None:
        """Log query execution."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info("query_executed", request_id=request_id, execution_time_ms=execution_time_ms, row_count=row_count, success=success)
        else:
            self.logger.info(f"Query executed: {request_id} - {execution_time_ms}ms - {row_count} rows - Success: {success}")
    
    def log_query_error(self, request_id: str, error: str, error_type: str = "execution") -> None:
        """Log query error."""
        if STRUCTLOG_AVAILABLE:
            self.logger.error("query_error", request_id=request_id, error=error, error_type=error_type)
        else:
            self.logger.error(f"Query error: {request_id} - {error_type}: {error}")
    
    def log_pii_incident(self, request_id: str, user_id: str, pii_columns: list) -> None:
        """Log PII incident."""
        if STRUCTLOG_AVAILABLE:
            self.logger.warning("pii_incident", request_id=request_id, user_id=user_id, pii_columns=pii_columns)
        else:
            self.logger.warning(f"PII incident: {request_id} by {user_id} - columns: {pii_columns}")
    
    def log_security_violation(self, request_id: str, user_id: str, violation_type: str, details: str) -> None:
        """Log security violation."""
        if STRUCTLOG_AVAILABLE:
            self.logger.warning("security_violation", request_id=request_id, user_id=user_id, violation_type=violation_type, details=details)
        else:
            self.logger.warning(f"Security violation: {request_id} by {user_id} - {violation_type}: {details}")


class AuditLogger:
    """Audit logger for compliance and security."""
    
    def __init__(self):
        if STRUCTLOG_AVAILABLE:
            self.logger = structlog.get_logger("audit")
        else:
            self.logger = logging.getLogger("audit")
    
    def log_user_action(self, user_id: str, action: str, resource: str, details: Dict[str, Any]) -> None:
        """Log user action for audit trail."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info("user_action", user_id=user_id, action=action, resource=resource, details=details, timestamp=datetime.utcnow().isoformat())
        else:
            self.logger.info(f"User action: {user_id} - {action} on {resource}")
    
    def log_data_access(self, user_id: str, table: str, columns: list, row_count: int) -> None:
        """Log data access for audit trail."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info("data_access", user_id=user_id, table=table, columns=columns, row_count=row_count, timestamp=datetime.utcnow().isoformat())
        else:
            self.logger.info(f"Data access: {user_id} - {table} ({len(columns)} columns, {row_count} rows)")
    
    def log_configuration_change(self, user_id: str, change_type: str, old_value: Any, new_value: Any) -> None:
        """Log configuration changes."""
        if STRUCTLOG_AVAILABLE:
            self.logger.info("configuration_change", user_id=user_id, change_type=change_type, old_value=old_value, new_value=new_value, timestamp=datetime.utcnow().isoformat())
        else:
            self.logger.info(f"Config change: {user_id} - {change_type}")


# Global logger instances
query_logger = QueryLogger()
audit_logger = AuditLogger()