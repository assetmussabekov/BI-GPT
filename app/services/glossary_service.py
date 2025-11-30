"""Business glossary service."""

import yaml
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from ..models.glossary import Glossary, BusinessTerm, TableMapping
from ..config import settings

logger = logging.getLogger(__name__)


class GlossaryService:
    """Service for managing business glossary."""
    
    def __init__(self, glossary_path: Optional[str] = None):
        """Initialize glossary service."""
        self.glossary_path = glossary_path or settings.glossary_path
        self._glossary: Optional[Glossary] = None
        self._load_glossary()
    
    def _load_glossary(self) -> None:
        """Load glossary from YAML file."""
        try:
            with open(self.glossary_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self._glossary = Glossary(**data)
                logger.info(f"Loaded glossary version {self._glossary.version}")
        except Exception as e:
            logger.error(f"Failed to load glossary: {e}")
            raise
    
    def get_glossary(self) -> Glossary:
        """Get current glossary."""
        if self._glossary is None:
            self._load_glossary()
        return self._glossary
    
    def find_term(self, text: str) -> Optional[BusinessTerm]:
        """Find business term by text (exact match or synonym)."""
        glossary = self.get_glossary()
        
        # First try exact match with canonical names
        text_lower = text.lower().strip()
        if text_lower in glossary.terms:
            return glossary.terms[text_lower]
        
        # Then try synonyms
        return glossary.get_term_by_synonym(text)
    
    def find_related_terms(self, text: str, limit: int = 5) -> List[BusinessTerm]:
        """Find related terms based on text similarity."""
        glossary = self.get_glossary()
        related_terms = []
        
        text_lower = text.lower().strip()
        
        for term in glossary.terms.values():
            # Check if text appears in any synonym
            for synonym in term.synonyms:
                if text_lower in synonym.lower() or synonym.lower() in text_lower:
                    related_terms.append(term)
                    break
            
            # Check if text appears in description
            if text_lower in term.description.lower():
                related_terms.append(term)
        
        return related_terms[:limit]
    
    def get_table_schema(self, table_name: str) -> Optional[TableMapping]:
        """Get table schema by name."""
        glossary = self.get_glossary()
        return glossary.table_mappings.get(table_name)
    
    def get_pii_columns(self) -> List[str]:
        """Get list of all PII columns."""
        return self.get_glossary().get_pii_columns()
    
    def get_permitted_tables(self) -> List[str]:
        """Get list of permitted tables."""
        return self.get_glossary().get_permitted_tables()
    
    def extract_business_terms(self, question: str) -> List[BusinessTerm]:
        """Extract business terms from natural language question."""
        terms = []
        words = question.lower().split()
        
        # Look for exact matches first
        for word in words:
            term = self.find_term(word)
            if term and term not in terms:
                terms.append(term)
        
        # Look for multi-word terms
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            term = self.find_term(bigram)
            if term and term not in terms:
                terms.append(term)
        
        # Look for related terms
        related = self.find_related_terms(question)
        for term in related:
            if term not in terms:
                terms.append(term)
        
        return terms
    
    def build_context_for_llm(self, question: str) -> Dict[str, Any]:
        """Build context dictionary for LLM prompt."""
        glossary = self.get_glossary()
        terms = self.extract_business_terms(question)
        
        context = {
            "question": question,
            "business_terms": [
                {
                    "canonical_name": term.canonical_name,
                    "synonyms": term.synonyms,
                    "expression": term.expression,
                    "description": term.description,
                    "required_tables": term.required_tables,
                    "category": term.category
                }
                for term in terms
            ],
            "permitted_tables": glossary.get_permitted_tables(),
            "pii_columns": glossary.get_pii_columns(),
            "table_schemas": {
                table_name: {
                    "description": table.description,
                    "columns": [
                        {
                            "name": col.name,
                            "type": col.type,
                            "description": col.description,
                            "is_pii": col.is_pii
                        }
                        for col in table.columns
                    ]
                }
                for table_name, table in glossary.table_mappings.items()
            }
        }
        
        return context