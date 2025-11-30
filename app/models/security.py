"""Security models for BI-GPT."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SecurityLevel(str, Enum):
    """Security levels for queries."""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class PIIFlag(str, Enum):
    """PII flag types."""
    NONE = "none"
    DETECTED = "detected"
    BLOCKED = "blocked"


class SecurityCheck(BaseModel):
    """Security check result."""
    level: SecurityLevel = Field(..., description="Security level")
    pii_flag: PIIFlag = Field(default=PIIFlag.NONE, description="PII detection flag")
    blocked_operations: List[str] = Field(default_factory=list, description="Blocked SQL operations")
    warnings: List[str] = Field(default_factory=list, description="Security warnings")
    estimated_cost: Optional[int] = Field(default=None, description="Estimated query cost")
    is_safe: bool = Field(..., description="Whether query is safe to execute")
    
    @property
    def should_block(self) -> bool:
        """Check if query should be blocked."""
        return self.level in [SecurityLevel.DANGEROUS, SecurityLevel.BLOCKED] or self.pii_flag == PIIFlag.BLOCKED


class AuditLog(BaseModel):
    """Audit log entry."""
    request_id: str = Field(..., description="Request identifier")
    user_id: str = Field(..., description="User identifier")
    timestamp: str = Field(..., description="Timestamp")
    original_question: str = Field(..., description="Original natural language question")
    generated_sql: str = Field(..., description="Generated SQL query")
    security_check: SecurityCheck = Field(..., description="Security check result")
    execution_time_ms: Optional[float] = Field(default=None, description="Execution time")
    row_count: Optional[int] = Field(default=None, description="Number of rows returned")
    error_message: Optional[str] = Field(default=None, description="Error message if any")
    ip_address: Optional[str] = Field(default=None, description="Client IP address")
    user_agent: Optional[str] = Field(default=None, description="Client user agent")