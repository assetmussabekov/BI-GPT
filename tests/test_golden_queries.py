"""Tests for golden queries validation."""

import pytest
import yaml
from pathlib import Path

from app.services.glossary_service import GlossaryService
from app.services.sql_generator import SQLGenerator
from app.services.security_service import SecurityService
from app.models.query import QueryRequest


class TestGoldenQueries:
    """Test cases for golden queries validation."""
    
    @pytest.fixture
    def golden_queries(self):
        """Load golden queries from YAML."""
        queries_path = Path(__file__).parent.parent / "data" / "golden_queries.yaml"
        with open(queries_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    @pytest.fixture
    def services(self):
        """Initialize services."""
        glossary_service = GlossaryService()
        glossary = glossary_service.get_glossary()
        sql_generator = SQLGenerator(glossary)
        security_service = SecurityService(glossary)
        
        return {
            "glossary_service": glossary_service,
            "sql_generator": sql_generator,
            "security_service": security_service
        }
    
    def test_golden_queries_loaded(self, golden_queries):
        """Test that golden queries are loaded correctly."""
        assert "queries" in golden_queries
        assert len(golden_queries["queries"]) > 0
        
        # Check structure of first query
        first_query = golden_queries["queries"][0]
        required_fields = ["id", "natural_language", "expected_sql", "business_terms", "tables_used"]
        for field in required_fields:
            assert field in first_query
    
    @pytest.mark.parametrize("query_data", [
        {"id": "gross_profit_daily", "difficulty": "easy"},
        {"id": "revenue_monthly", "difficulty": "easy"},
        {"id": "gross_margin_regional", "difficulty": "medium"},
    ])
    def test_basic_queries(self, query_data, golden_queries, services):
        """Test basic golden queries."""
        # Find query by ID
        query = next((q for q in golden_queries["queries"] if q["id"] == query_data["id"]), None)
        assert query is not None
        
        # Create request
        request = QueryRequest(
            question=query["natural_language"],
            user_id="test_user",
            user_role="manager"
        )
        
        # Generate SQL
        sql_result = services["sql_generator"].generate_sql(request)
        
        # Basic validation
        assert sql_result.get("sql") is not None
        assert sql_result.get("confidence", 0) > 0
        assert not sql_result.get("needs_clarification", False)
        
        # Security check
        security_check = services["security_service"].check_query_security(
            sql_result["sql"], 
            request.user_role
        )
        assert security_check.is_safe
    
    def test_business_terms_extraction(self, golden_queries, services):
        """Test business terms extraction from golden queries."""
        for query in golden_queries["queries"][:5]:  # Test first 5 queries
            question = query["natural_language"]
            terms = services["glossary_service"].extract_business_terms(question)
            
            # Should find at least one business term
            assert len(terms) > 0, f"No business terms found for: {question}"
            
            # Check that expected business terms are found
            expected_terms = query.get("business_terms", [])
            found_terms = [term.canonical_name for term in terms]
            
            for expected_term in expected_terms:
                assert expected_term in found_terms, f"Expected term {expected_term} not found for: {question}"
    
    def test_table_usage_validation(self, golden_queries, services):
        """Test that queries use only permitted tables."""
        permitted_tables = services["glossary_service"].get_permitted_tables()
        
        for query in golden_queries["queries"]:
            expected_tables = query.get("tables_used", [])
            
            for table in expected_tables:
                assert table in permitted_tables, f"Table {table} not in permitted tables for query: {query['id']}"
    
    def test_sql_syntax_validation(self, golden_queries, services):
        """Test SQL syntax validation for expected queries."""
        for query in golden_queries["queries"][:3]:  # Test first 3 queries
            expected_sql = query["expected_sql"].strip()
            
            # Basic syntax checks
            assert expected_sql.upper().startswith("SELECT"), f"Query {query['id']} doesn't start with SELECT"
            assert ";" in expected_sql, f"Query {query['id']} doesn't end with semicolon"
            
            # Security check
            security_check = services["security_service"].check_query_security(expected_sql)
            assert security_check.is_safe, f"Expected SQL for {query['id']} failed security check"
    
    def test_query_categories(self, golden_queries):
        """Test that queries have valid categories."""
        valid_categories = ["financial", "product", "location", "customer", "sales", "time"]
        
        for query in golden_queries["queries"]:
            category = query.get("category")
            assert category in valid_categories, f"Invalid category {category} for query {query['id']}"
    
    def test_difficulty_levels(self, golden_queries):
        """Test that queries have valid difficulty levels."""
        valid_difficulties = ["easy", "medium", "hard"]
        
        for query in golden_queries["queries"]:
            difficulty = query.get("difficulty")
            assert difficulty in valid_difficulties, f"Invalid difficulty {difficulty} for query {query['id']}"