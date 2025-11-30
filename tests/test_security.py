"""Tests for security service."""

import pytest

from app.services.security_service import SecurityService
from app.models.glossary import Glossary
from app.models.security import SecurityLevel, PIIFlag


class TestSecurityService:
    """Test cases for SecurityService."""
    
    @pytest.fixture
    def glossary(self):
        """Create test glossary."""
        return Glossary(
            version="1.0",
            last_updated="2024-01-01",
            terms={},
            table_mappings={
                "sales": {
                    "description": "Sales table",
                    "columns": [
                        {"name": "order_id", "type": "integer", "description": "Order ID", "is_pii": False},
                        {"name": "customer_id", "type": "integer", "description": "Customer ID", "is_pii": True},
                        {"name": "revenue", "type": "decimal", "description": "Revenue", "is_pii": False}
                    ]
                }
            }
        )
    
    @pytest.fixture
    def security_service(self, glossary):
        """Create security service instance."""
        return SecurityService(glossary)
    
    def test_safe_query(self, security_service):
        """Test safe query passes security check."""
        sql = "SELECT SUM(revenue) FROM sales WHERE order_date >= '2024-01-01'"
        check = security_service.check_query_security(sql)
        
        assert check.level == SecurityLevel.SAFE
        assert check.is_safe is True
        assert check.pii_flag == PIIFlag.NONE
        assert len(check.blocked_operations) == 0
    
    def test_dangerous_operations_blocked(self, security_service):
        """Test dangerous operations are blocked."""
        dangerous_queries = [
            "UPDATE sales SET revenue = 0",
            "DELETE FROM sales",
            "DROP TABLE sales",
            "INSERT INTO sales VALUES (1, 2, 3)",
            "SELECT * FROM pg_catalog.pg_user"
        ]
        
        for sql in dangerous_queries:
            check = security_service.check_query_security(sql)
            assert check.level == SecurityLevel.BLOCKED
            assert check.is_safe is False
            assert len(check.blocked_operations) > 0
    
    def test_pii_access_detected(self, security_service):
        """Test PII access is detected."""
        sql = "SELECT customer_id, revenue FROM sales"
        check = security_service.check_query_security(sql)
        
        assert check.pii_flag == PIIFlag.DETECTED
        assert check.level == SecurityLevel.DANGEROUS
    
    def test_warning_patterns(self, security_service):
        """Test warning patterns are flagged."""
        sql = "SELECT * FROM sales ORDER BY 1 LIMIT 10000"
        check = security_service.check_query_security(sql)
        
        assert check.level == SecurityLevel.WARNING
        assert len(check.warnings) > 0
        assert check.is_safe is True  # Warnings don't block execution
    
    def test_estimate_query_cost(self, security_service):
        """Test query cost estimation."""
        simple_sql = "SELECT * FROM sales LIMIT 10"
        complex_sql = "SELECT * FROM sales s1 JOIN sales s2 ON s1.order_id = s2.order_id GROUP BY s1.order_id ORDER BY s1.order_id"
        
        simple_cost = security_service._estimate_query_cost(simple_sql)
        complex_cost = security_service._estimate_query_cost(complex_sql)
        
        assert simple_cost < complex_cost
        assert simple_cost > 0
        assert complex_cost > 0
    
    def test_sanitize_query(self, security_service):
        """Test query sanitization."""
        sql = "SELECT * FROM sales"
        sanitized = security_service.sanitize_query(sql)
        
        assert sanitized.startswith("/* AGENT:GEN v=1 */")
        assert "SELECT * FROM sales" in sanitized
    
    def test_validate_table_access(self, security_service):
        """Test table access validation."""
        valid_sql = "SELECT * FROM sales"
        invalid_sql = "SELECT * FROM unauthorized_table"
        
        valid_tables = security_service.validate_table_access(valid_sql)
        invalid_tables = security_service.validate_table_access(invalid_sql)
        
        assert len(valid_tables) == 0
        assert len(invalid_tables) > 0
        assert "unauthorized_table" in invalid_tables