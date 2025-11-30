"""Query models for BI-GPT."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class QueryStatus(str, Enum):
    """Query execution status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class QueryRequest(BaseModel):
    """Request for natural language query."""
    question: str = Field(..., description="Natural language question")
    user_id: str = Field(..., description="User identifier")
    user_role: str = Field(default="manager", description="User role")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    max_rows: Optional[int] = Field(default=1000, description="Maximum rows to return")
    timeout_seconds: Optional[int] = Field(default=30, description="Query timeout")


class QueryResult(BaseModel):
    """Query execution result."""
    data: List[Dict[str, Any]] = Field(..., description="Query result data")
    columns: List[str] = Field(..., description="Column names")
    row_count: int = Field(..., description="Number of rows returned")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    sql_query: str = Field(..., description="Generated SQL query")
    confidence_score: float = Field(..., description="Confidence score (0-1)")


class QueryExplanation(BaseModel):
    """Explanation of the query."""
    tables_used: List[str] = Field(..., description="Tables used in the query")
    filters_applied: List[str] = Field(default_factory=list, description="Filters applied")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made")
    formulas: List[str] = Field(default_factory=list, description="Formulas used")
    business_terms: List[str] = Field(default_factory=list, description="Business terms used")


class QueryResponse(BaseModel):
    """Response to query request."""
    request_id: str = Field(..., description="Unique request identifier")
    status: QueryStatus = Field(..., description="Query status")
    result: Optional[QueryResult] = Field(default=None, description="Query result")
    explanation: Optional[QueryExplanation] = Field(default=None, description="Query explanation")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    
    @property
    def is_successful(self) -> bool:
        """Check if query was successful."""
        return self.status == QueryStatus.COMPLETED and self.result is not None
    
    @property
    def is_failed(self) -> bool:
        """Check if query failed."""
        return self.status in [QueryStatus.FAILED, QueryStatus.REJECTED]