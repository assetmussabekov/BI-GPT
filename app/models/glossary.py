"""Business glossary models."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TermCategory(str, Enum):
    """Categories for business terms."""
    FINANCIAL = "financial"
    TIME = "time"
    PRODUCT = "product"
    LOCATION = "location"
    CUSTOMER = "customer"
    SALES = "sales"


class BusinessTerm(BaseModel):
    """Business term definition."""
    canonical_name: str = Field(..., description="Canonical name of the term")
    synonyms: List[str] = Field(default_factory=list, description="List of synonyms")
    expression: str = Field(..., description="SQL expression or formula")
    description: str = Field(..., description="Human-readable description")
    required_tables: List[str] = Field(default_factory=list, description="Required database tables")
    default_grain: str = Field(..., description="Default time grain (day, week, month, etc.)")
    owner: str = Field(..., description="Owner of the term")
    category: TermCategory = Field(..., description="Category of the term")
    is_pii: bool = Field(default=False, description="Whether this term contains PII")


class ColumnDefinition(BaseModel):
    """Database column definition."""
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type")
    description: str = Field(..., description="Column description")
    is_pii: bool = Field(default=False, description="Whether column contains PII")


class TableMapping(BaseModel):
    """Database table mapping."""
    description: str = Field(..., description="Table description")
    columns: List[ColumnDefinition] = Field(..., description="List of columns")


class Glossary(BaseModel):
    """Complete business glossary."""
    version: str = Field(..., description="Glossary version")
    last_updated: str = Field(..., description="Last update date")
    terms: Dict[str, BusinessTerm] = Field(..., description="Business terms")
    table_mappings: Dict[str, TableMapping] = Field(..., description="Table mappings")
    
    def get_term_by_synonym(self, synonym: str) -> Optional[BusinessTerm]:
        """Find term by synonym."""
        synonym_lower = synonym.lower().strip()
        for term in self.terms.values():
            if synonym_lower in [s.lower() for s in term.synonyms]:
                return term
        return None
    
    def get_pii_columns(self) -> List[str]:
        """Get list of all PII columns."""
        pii_columns = []
        for table_name, table_mapping in self.table_mappings.items():
            for column in table_mapping.columns:
                if column.is_pii:
                    pii_columns.append(f"{table_name}.{column.name}")
        return pii_columns
    
    def get_permitted_tables(self) -> List[str]:
        """Get list of permitted tables."""
        return list(self.table_mappings.keys())