"""Tests for glossary service."""

import pytest
import yaml
from pathlib import Path

from app.services.glossary_service import GlossaryService
from app.models.glossary import Glossary, BusinessTerm, TermCategory


class TestGlossaryService:
    """Test cases for GlossaryService."""
    
    @pytest.fixture
    def glossary_service(self):
        """Create glossary service instance."""
        return GlossaryService()
    
    def test_load_glossary(self, glossary_service):
        """Test glossary loading."""
        glossary = glossary_service.get_glossary()
        assert isinstance(glossary, Glossary)
        assert glossary.version == "1.0"
        assert len(glossary.terms) > 0
        assert len(glossary.table_mappings) > 0
    
    def test_find_term_by_canonical_name(self, glossary_service):
        """Test finding term by canonical name."""
        term = glossary_service.find_term("gross_margin")
        assert term is not None
        assert term.canonical_name == "gross_margin"
        assert term.category == TermCategory.FINANCIAL
    
    def test_find_term_by_synonym(self, glossary_service):
        """Test finding term by synonym."""
        term = glossary_service.find_term("маржа")
        assert term is not None
        assert term.canonical_name == "gross_margin"
        assert "маржа" in term.synonyms
    
    def test_find_related_terms(self, glossary_service):
        """Test finding related terms."""
        related = glossary_service.find_related_terms("прибыль")
        assert len(related) > 0
        # Should find gross_profit term
        assert any(term.canonical_name == "gross_profit" for term in related)
    
    def test_extract_business_terms(self, glossary_service):
        """Test extracting business terms from question."""
        question = "Прибыль за последние 2 дня для всех магазинов"
        terms = glossary_service.extract_business_terms(question)
        assert len(terms) > 0
        # Should find gross_profit term
        assert any(term.canonical_name == "gross_profit" for term in terms)
    
    def test_get_pii_columns(self, glossary_service):
        """Test getting PII columns."""
        pii_columns = glossary_service.get_pii_columns()
        assert len(pii_columns) > 0
        # Should include customer_id columns
        assert any("customer_id" in col for col in pii_columns)
    
    def test_get_permitted_tables(self, glossary_service):
        """Test getting permitted tables."""
        tables = glossary_service.get_permitted_tables()
        assert len(tables) > 0
        assert "sales" in tables
        assert "products" in tables
        assert "stores" in tables
    
    def test_build_context_for_llm(self, glossary_service):
        """Test building context for LLM."""
        question = "Прибыль за последние 2 дня"
        context = glossary_service.build_context_for_llm(question)
        
        assert "question" in context
        assert "business_terms" in context
        assert "permitted_tables" in context
        assert "pii_columns" in context
        assert "table_schemas" in context
        
        assert context["question"] == question
        assert len(context["business_terms"]) > 0
        assert len(context["permitted_tables"]) > 0