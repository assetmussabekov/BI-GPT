"""SQL generator service using LLM."""

import json
import re
from typing import Dict, Any, Optional, List
import logging

from ..config import settings
from ..models.glossary import Glossary
from ..models.query import QueryRequest

# Optional OpenAI import for demo mode
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Service for generating SQL from natural language using LLM."""
    
    def __init__(self, glossary: Glossary):
        """Initialize SQL generator."""
        self.glossary = glossary
        if OPENAI_AVAILABLE and settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
        else:
            self.client = None
            self.model = None
    
    def generate_sql(self, request: QueryRequest) -> Dict[str, Any]:
        """Generate SQL query from natural language question."""
        try:
            # Check if OpenAI is available and configured
            if not self.client:
                return {
                    "sql": None,
                    "confidence": 0.0,
                    "error": "OpenAI API not configured",
                    "needs_clarification": False
                }
            
            # Build context for LLM
            context = self._build_llm_context(request)
            
            # Generate SQL using LLM
            sql_response = self._call_llm(context)
            
            # Parse and validate response
            result = self._parse_llm_response(sql_response)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate SQL: {e}")
            return {
                "sql": None,
                "confidence": 0.0,
                "error": str(e),
                "needs_clarification": False
            }
    
    def _build_llm_context(self, request: QueryRequest) -> Dict[str, Any]:
        """Build context for LLM prompt."""
        # Extract business terms from question
        terms = self.glossary.extract_business_terms(request.question)
        
        # Build table schemas
        table_schemas = {}
        for table_name, table_mapping in self.glossary.table_mappings.items():
            table_schemas[table_name] = {
                "description": table_mapping.description,
                "columns": [
                    {
                        "name": col.name,
                        "type": col.type,
                        "description": col.description,
                        "is_pii": col.is_pii
                    }
                    for col in table_mapping.columns
                ]
            }
        
        context = {
            "question": request.question,
            "user_role": request.user_role,
            "max_rows": request.max_rows or 1000,
            "business_terms": [
                {
                    "canonical_name": term.canonical_name,
                    "synonyms": term.synonyms,
                    "expression": term.expression,
                    "description": term.description,
                    "required_tables": term.required_tables,
                    "category": term.category.value
                }
                for term in terms
            ],
            "permitted_tables": self.glossary.get_permitted_tables(),
            "pii_columns": self.glossary.get_pii_columns(),
            "table_schemas": table_schemas
        }
        
        return context
    
    def _call_llm(self, context: Dict[str, Any]) -> str:
        """Call LLM to generate SQL."""
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for LLM."""
        return """You are an expert SQL generator for business intelligence queries. Your task is to convert natural language questions into safe, optimized SQL queries.

RULES:
1. Generate ONLY SELECT queries - no INSERT, UPDATE, DELETE, or DDL statements
2. Use only the provided table schemas and business terms
3. Do NOT access PII columns (marked as is_pii: true)
4. Add appropriate LIMIT clauses for large result sets
5. Use proper JOINs and WHERE clauses for filtering
6. Include business term expressions when relevant
7. Output SQL between <<<SQL>>> markers
8. If the question is ambiguous, return JSON with clarification request

OUTPUT FORMAT:
- For valid queries: SQL between <<<SQL>>> markers
- For clarification: JSON with {"clarify": true, "questions": [...]}

EXAMPLES:

Question: "Прибыль за последние 2 дня"
<<<SQL>>>
SELECT 
  DATE(order_date) AS day,
  SUM(revenue - cogs) AS gross_profit
FROM sales 
WHERE order_date >= current_date - INTERVAL '2 day'
  AND order_date < current_date
GROUP BY DATE(order_date)
ORDER BY day;
<<<SQL>>>

Question: "Маржинальность по регионам за июль"
<<<SQL>>>
SELECT 
  s.region,
  SUM(s.revenue - s.cogs) / NULLIF(SUM(s.revenue), 0) * 100 AS gross_margin_pct
FROM sales s
JOIN stores st ON s.store_id = st.store_id
WHERE s.order_date >= '2024-07-01' 
  AND s.order_date < '2024-08-01'
GROUP BY s.region
ORDER BY gross_margin_pct DESC;
<<<SQL>>>"""
    
    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        """Build user prompt with context."""
        prompt = f"""Question: {context['question']}

User Role: {context['user_role']}
Max Rows: {context['max_rows']}

Business Terms Found:
{json.dumps(context['business_terms'], indent=2, ensure_ascii=False)}

Permitted Tables: {', '.join(context['permitted_tables'])}
PII Columns (DO NOT ACCESS): {', '.join(context['pii_columns'])}

Table Schemas:
{json.dumps(context['table_schemas'], indent=2, ensure_ascii=False)}

Generate SQL query for this question:"""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response and extract SQL."""
        response = response.strip()
        
        # Check if response is a clarification request
        if response.startswith('{') and '"clarify"' in response:
            try:
                clarification = json.loads(response)
                return {
                    "sql": None,
                    "confidence": 0.0,
                    "needs_clarification": True,
                    "clarification_questions": clarification.get("questions", [])
                }
            except json.JSONDecodeError:
                pass
        
        # Extract SQL from markers
        sql_match = re.search(r'<<<SQL>>>(.*?)<<<SQL>>>', response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1).strip()
            
            # Calculate confidence based on response quality
            confidence = self._calculate_confidence(sql, response)
            
            return {
                "sql": sql,
                "confidence": confidence,
                "needs_clarification": False,
                "raw_response": response
            }
        
        # If no SQL markers found, try to extract SQL from response
        sql_lines = []
        in_sql = False
        
        for line in response.split('\n'):
            line = line.strip()
            if line.upper().startswith('SELECT'):
                in_sql = True
                sql_lines.append(line)
            elif in_sql and (line.endswith(';') or line == ''):
                sql_lines.append(line)
                break
            elif in_sql:
                sql_lines.append(line)
        
        if sql_lines:
            sql = '\n'.join(sql_lines)
            confidence = self._calculate_confidence(sql, response)
            
            return {
                "sql": sql,
                "confidence": confidence,
                "needs_clarification": False,
                "raw_response": response
            }
        
        return {
            "sql": None,
            "confidence": 0.0,
            "error": "Could not extract SQL from response",
            "raw_response": response
        }
    
    def _calculate_confidence(self, sql: str, response: str) -> float:
        """Calculate confidence score for generated SQL."""
        confidence = 0.5  # Base confidence
        
        # Check for proper SQL structure
        if sql.upper().startswith('SELECT'):
            confidence += 0.2
        
        # Check for business terms usage
        business_terms = [term.canonical_name for term in self.glossary.terms.values()]
        for term in business_terms:
            if term.lower() in sql.lower():
                confidence += 0.1
        
        # Check for proper JOINs
        if 'JOIN' in sql.upper():
            confidence += 0.1
        
        # Check for WHERE clause
        if 'WHERE' in sql.upper():
            confidence += 0.1
        
        # Check for GROUP BY (indicates aggregation)
        if 'GROUP BY' in sql.upper():
            confidence += 0.1
        
        # Penalize for potential issues
        if 'SELECT *' in sql.upper():
            confidence -= 0.2
        
        if len(sql) < 50:  # Too short
            confidence -= 0.2
        
        return min(1.0, max(0.0, confidence))