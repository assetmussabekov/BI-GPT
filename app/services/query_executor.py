"""Query executor service."""

import time
from typing import Dict, Any, List, Optional
import logging

# Optional imports for demo mode
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    create_engine = None
    text = None
    SQLAlchemyError = Exception

from ..config import settings
from ..models.query import QueryResult
from ..models.security import SecurityCheck

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Service for executing SQL queries safely."""
    
    def __init__(self):
        """Initialize query executor."""
        self.max_rows = settings.max_query_rows
        self.timeout = settings.query_timeout_seconds
        
        # Initialize engine only if SQLAlchemy is available
        if SQLALCHEMY_AVAILABLE:
            self.engine = create_engine(settings.database_url)
        else:
            self.engine = None
    
    def execute_query(
        self, 
        sql: str, 
        security_check: Optional[SecurityCheck] = None,
        max_rows: Optional[int] = None
    ) -> QueryResult:
        """Execute SQL query safely."""
        if security_check and not security_check.is_safe:
            raise ValueError(f"Query is not safe to execute: {security_check.level}")
        
        start_time = time.time()
        
        # Demo mode - return mock result
        if not self.engine:
            execution_time = (time.time() - start_time) * 1000
            
            # Extract columns from SQL for demo
            columns = self._extract_columns_from_sql(sql)
            
            return QueryResult(
                data=[],  # Empty data for demo
                columns=columns,
                row_count=len(columns) * 5,  # Mock row count
                execution_time_ms=int(execution_time),
                sql_query=sql,
                confidence_score=1.0
            )
        
        try:
            # Set query timeout
            with self.engine.connect() as conn:
                # Set session parameters for safety
                conn.execute(text("SET statement_timeout = :timeout"), 
                           {"timeout": f"{self.timeout * 1000}ms"})
                conn.execute(text("SET max_rows = :max_rows"), 
                           {"max_rows": max_rows or self.max_rows})
                
                # Execute query
                result = conn.execute(text(sql))
                
                # Fetch results
                rows = result.fetchall()
                columns = list(result.keys())
                
                # Convert to list of dictionaries
                data = [dict(zip(columns, row)) for row in rows]
                
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                
                return QueryResult(
                    data=data,
                    columns=columns,
                    row_count=len(data),
                    execution_time_ms=execution_time,
                    sql_query=sql,
                    confidence_score=1.0  # Will be updated by caller
                )
                
        except SQLAlchemyError as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"SQL execution error: {e}")
            raise ValueError(f"Query execution failed: {str(e)}")
    
    def validate_query_syntax(self, sql: str) -> bool:
        """Validate SQL query syntax without executing."""
        if not self.engine:
            # Demo mode - basic validation
            return sql.strip().upper().startswith('SELECT')
            
        try:
            with self.engine.connect() as conn:
                # Use EXPLAIN to validate syntax
                explain_sql = f"EXPLAIN {sql}"
                conn.execute(text(explain_sql))
                return True
        except SQLAlchemyError:
            return False
    
    def get_query_plan(self, sql: str) -> Dict[str, Any]:
        """Get query execution plan."""
        try:
            with self.engine.connect() as conn:
                explain_sql = f"EXPLAIN (FORMAT JSON) {sql}"
                result = conn.execute(text(explain_sql))
                plan = result.fetchone()[0]
                return plan
        except SQLAlchemyError as e:
            logger.error(f"Failed to get query plan: {e}")
            return {"error": str(e)}
    
    def estimate_query_cost(self, sql: str) -> int:
        """Estimate query execution cost."""
        try:
            plan = self.get_query_plan(sql)
            if "error" in plan:
                return 1000  # High cost for failed plans
            
            # Extract cost from plan (PostgreSQL specific)
            total_cost = 0
            for node in plan[0].get("Plan", {}).get("Plans", []):
                total_cost += node.get("Total Cost", 0)
            
            return int(total_cost)
        except Exception:
            return 1000  # Default high cost
    
    def test_connection(self) -> bool:
        """Test database connection."""
        if not self.engine:
            return False  # Demo mode - no real connection
            
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def _extract_columns_from_sql(self, sql: str) -> List[str]:
        """Extract column names from SQL for demo mode."""
        import re
        
        # Simple column extraction for demo
        columns = []
        
        # Look for SELECT ... FROM pattern
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            
            # Split by comma and clean up
            for col in select_clause.split(','):
                col = col.strip()
                
                # Remove AS aliases
                if ' AS ' in col.upper():
                    col = col.split(' AS ')[-1].strip()
                
                # Remove function calls (keep only the alias)
                if '(' in col and ')' in col:
                    # Extract alias after AS
                    if ' AS ' in col.upper():
                        col = col.split(' AS ')[-1].strip()
                    else:
                        # Use function name
                        col = col.split('(')[0].strip()
                
                if col and col not in columns:
                    columns.append(col)
        
        # Fallback columns if nothing found
        if not columns:
            columns = ['column1', 'column2', 'column3']
        
        return columns