"""Security service for SQL query validation."""

import re
from typing import List, Optional, Dict, Any
import logging

from ..models.security import SecurityCheck, SecurityLevel, PIIFlag
from ..models.glossary import Glossary

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for SQL query security validation."""
    
    # Dangerous SQL operations that should be blocked
    DANGEROUS_OPERATIONS = [
        r'\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)\b',
        r'\b(COPY|UNLOAD|LOAD)\b',
        r'\b(GRANT|REVOKE|DENY)\b',
        r'\b(EXEC|EXECUTE|CALL)\b',
        r'\b(pg_sleep|sleep|waitfor)\b',
        r'\b(SYSTEM|ADMIN|ROOT)\b',
        r'\b(INFORMATION_SCHEMA|pg_catalog|sys)\b',
        r'\b(UNION\s+SELECT|UNION\s+ALL)\b',
        r'\b(HAVING\s+1=1|WHERE\s+1=1)\b',
        r'\b(OR\s+1=1|AND\s+1=1)\b'
    ]
    
    # Warning patterns that should be flagged
    WARNING_PATTERNS = [
        r'\b(SELECT\s+\*)\b',  # SELECT *
        r'\b(ORDER\s+BY\s+\d+)\b',  # ORDER BY number
        r'\b(LIMIT\s+\d{4,})\b',  # Large LIMIT
        r'\b(JOIN.*JOIN.*JOIN)\b',  # Multiple JOINs
    ]
    
    def __init__(self, glossary: Glossary):
        """Initialize security service."""
        self.glossary = glossary
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        self.dangerous_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_OPERATIONS]
        self.warning_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.WARNING_PATTERNS]
    
    def check_query_security(self, sql_query: str, user_role: str = "manager") -> SecurityCheck:
        """Check SQL query for security issues."""
        sql_upper = sql_query.upper()
        
        # Check for dangerous operations
        blocked_operations = []
        for pattern in self.dangerous_patterns:
            if pattern.search(sql_query):
                blocked_operations.append(pattern.pattern)
        
        # Check for PII access
        pii_flag = self._check_pii_access(sql_query)
        
        # Check for warnings
        warnings = []
        for pattern in self.warning_patterns:
            if pattern.search(sql_query):
                warnings.append(f"Potentially inefficient pattern: {pattern.pattern}")
        
        # Estimate query cost
        estimated_cost = self._estimate_query_cost(sql_query)
        
        # Determine security level
        if blocked_operations or pii_flag == PIIFlag.BLOCKED:
            level = SecurityLevel.BLOCKED
        elif pii_flag == PIIFlag.DETECTED:
            level = SecurityLevel.DANGEROUS
        elif warnings:
            level = SecurityLevel.WARNING
        else:
            level = SecurityLevel.SAFE
        
        # Check if query should be blocked
        is_safe = level in [SecurityLevel.SAFE, SecurityLevel.WARNING]
        
        return SecurityCheck(
            level=level,
            pii_flag=pii_flag,
            blocked_operations=blocked_operations,
            warnings=warnings,
            estimated_cost=estimated_cost,
            is_safe=is_safe
        )
    
    def _check_pii_access(self, sql_query: str) -> PIIFlag:
        """Check if query accesses PII columns."""
        pii_columns = self.glossary.get_pii_columns()
        
        for pii_column in pii_columns:
            # Check if PII column is referenced in SELECT, WHERE, or JOIN
            if re.search(rf'\b{pii_column}\b', sql_query, re.IGNORECASE):
                return PIIFlag.DETECTED
        
        return PIIFlag.NONE
    
    def _estimate_query_cost(self, sql_query: str) -> int:
        """Estimate query execution cost."""
        cost = 0
        
        # Base cost
        cost += 10
        
        # Cost for JOINs
        join_count = len(re.findall(r'\bJOIN\b', sql_query, re.IGNORECASE))
        cost += join_count * 50
        
        # Cost for GROUP BY
        if re.search(r'\bGROUP\s+BY\b', sql_query, re.IGNORECASE):
            cost += 100
        
        # Cost for ORDER BY
        if re.search(r'\bORDER\s+BY\b', sql_query, re.IGNORECASE):
            cost += 50
        
        # Cost for subqueries
        subquery_count = len(re.findall(r'\([^)]*SELECT[^)]*\)', sql_query, re.IGNORECASE))
        cost += subquery_count * 200
        
        # Cost for window functions
        window_count = len(re.findall(r'\bOVER\s*\(', sql_query, re.IGNORECASE))
        cost += window_count * 150
        
        return cost
    
    def sanitize_query(self, sql_query: str) -> str:
        """Sanitize SQL query by adding safety measures."""
        # Ensure query starts with SELECT
        if not sql_query.strip().upper().startswith('SELECT'):
            raise ValueError("Only SELECT queries are allowed")
        
        # Add LIMIT if not present and query might return many rows
        if not re.search(r'\bLIMIT\s+\d+\b', sql_query, re.IGNORECASE):
            # Check if query has potential for large result set
            if self._estimate_query_cost(sql_query) > 500:
                sql_query += " LIMIT 10000"
        
        # Add comment with generation info
        sql_query = f"/* AGENT:GEN v=1 */\n{sql_query}"
        
        return sql_query
    
    def validate_table_access(self, sql_query: str) -> List[str]:
        """Validate that query only accesses permitted tables."""
        permitted_tables = self.glossary.get_permitted_tables()
        accessed_tables = []
        
        # Extract table names from FROM and JOIN clauses
        from_pattern = r'\bFROM\s+(\w+)'
        join_pattern = r'\bJOIN\s+(\w+)'
        
        for pattern in [from_pattern, join_pattern]:
            matches = re.findall(pattern, sql_query, re.IGNORECASE)
            accessed_tables.extend(matches)
        
        # Check for unauthorized tables
        unauthorized = []
        for table in accessed_tables:
            if table not in permitted_tables:
                unauthorized.append(table)
        
        return unauthorized