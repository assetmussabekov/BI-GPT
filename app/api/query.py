"""Query API endpoints."""

import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging

from ..models.query import QueryRequest, QueryResponse, QueryStatus, QueryExplanation
from ..models.security import AuditLog
from ..services.glossary_service import GlossaryService
from ..services.sql_generator import SQLGenerator
from ..services.security_service import SecurityService
from ..services.query_executor import QueryExecutor
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/query", tags=["query"])

# Initialize services
glossary_service = GlossaryService()
glossary = glossary_service.get_glossary()
sql_generator = SQLGenerator(glossary)
security_service = SecurityService(glossary)
query_executor = QueryExecutor()



@router.post("/", response_model=QueryResponse)
async def execute_query(request: QueryRequest) -> QueryResponse:
    request_id = str(uuid.uuid4())

    # Check if OpenAI API key is configured
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        # Demo mode - return example SQL for common questions
        demo_result = _get_demo_sql(request.question)
        if demo_result:
            return QueryResponse(
                request_id=request_id,
                status=QueryStatus.COMPLETED,
                result=demo_result,
                explanation=_generate_demo_explanation(request.question, demo_result.sql_query)
            )
        else:
            return QueryResponse(
                request_id=request_id,
                status=QueryStatus.FAILED,
                error_message="Service temporarily unavailable: OpenAI API key not configured. Please contact administrator to set up the service.",
                result=None,
                explanation=None
            )

    try:
        # Generate SQL from question
        sql_result = sql_generator.generate_sql(request)
        if not sql_result.get("sql"):
            raise Exception(sql_result.get("error", "Failed to generate SQL"))

        # Security check
        security_check = security_service.check_query_security(sql_result["sql"], request.user_role)
        if not security_check.is_safe:
            raise Exception("Query failed security check: " + "; ".join(security_check.warnings))

        # Execute query
        query_result = query_executor.execute_query(sql_result["sql"])

        # Generate explanation
        explanation = _generate_explanation(request.question, sql_result["sql"], glossary_service)

        # Audit log (example, should be saved somewhere)
        audit_log = AuditLog(
            user_id=request.user_id,
            timestamp=str(uuid.uuid4()),  # Should be a real timestamp
            original_question=request.question,
            generated_sql=sql_result["sql"],
            security_check=security_check,
            execution_time_ms=query_result.execution_time_ms,
            row_count=query_result.row_count
        )
        logger.info(f"Query executed successfully: {audit_log}")

        return QueryResponse(
            request_id=request_id,
            status=QueryStatus.COMPLETED,
            result=query_result,
            explanation=explanation
        )

    except Exception as e:
        logger.error(f"Query execution failed {request_id}: {e}")
        
        # Определяем тип ошибки и показываем понятное сообщение
        error_message = str(e)
        if "API key" in error_message or "401" in error_message:
            user_message = "Service temporarily unavailable: OpenAI API key not configured. Please contact administrator."
        elif "database" in error_message.lower() or "connection" in error_message.lower():
            user_message = "Database temporarily unavailable. Please try again later or contact support."
        elif "timeout" in error_message.lower():
            user_message = "Request timeout. Please try with a simpler query or contact support."
        else:
            user_message = "Service temporarily unavailable. Please try again later or contact support."
        
        return QueryResponse(
            request_id=request_id,
            status=QueryStatus.FAILED,
            error_message=user_message,
            result=None
        )


@router.get("/{request_id}", response_model=QueryResponse)
async def get_query_status(request_id: str) -> QueryResponse:
    """Get query status by request ID."""
    # In a real implementation, this would query a database or cache
    # For now, return a placeholder response
    return QueryResponse(
        request_id=request_id,
        status=QueryStatus.COMPLETED,
        error_message="Query status not implemented yet"
    )


@router.post("/validate")
async def validate_query(request: QueryRequest) -> Dict[str, Any]:
    """Validate query without executing."""
    try:
        # Generate SQL
        sql_result = sql_generator.generate_sql(request)
        
        if not sql_result.get("sql"):
            return {
                "valid": False,
                "error": sql_result.get("error", "Failed to generate SQL"),
                "needs_clarification": sql_result.get("needs_clarification", False)
            }
        
        sql = sql_result["sql"]
        
        # Security check
        security_check = security_service.check_query_security(sql, request.user_role)
        
        # Syntax validation
        syntax_valid = query_executor.validate_query_syntax(sql)
        
        return {
            "valid": syntax_valid and security_check.is_safe,
            "sql": sql,
            "security_check": {
                "level": security_check.level,
                "is_safe": security_check.is_safe,
                "warnings": security_check.warnings,
                "blocked_operations": security_check.blocked_operations
            },
            "confidence": sql_result.get("confidence", 0.0),
            "needs_clarification": sql_result.get("needs_clarification", False)
        }
        
    except Exception as e:
        logger.error(f"Query validation failed: {e}")
        return {
            "valid": False,
            "error": str(e)
        }


def _generate_explanation(question: str, sql: str, glossary_service: GlossaryService) -> QueryExplanation:
    """Generate explanation for the query."""
    # Extract business terms used
    terms = glossary_service.extract_business_terms(question)
    business_terms = [term.canonical_name for term in terms]
    
    # Extract tables used from SQL
    import re
    table_pattern = r'\bFROM\s+(\w+)|JOIN\s+(\w+)'
    tables_used = list(set(re.findall(table_pattern, sql, re.IGNORECASE)))
    tables_used = [table[0] or table[1] for table in tables_used]
    
    # Extract filters
    where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
    filters_applied = [where_match.group(1).strip()] if where_match else []
    
    # Generate assumptions
    assumptions = []
    if "current_date" in sql:
        assumptions.append("Использована текущая дата для временных фильтров")
    if "LIMIT" in sql:
        assumptions.append("Добавлено ограничение на количество строк")
    
    # Extract formulas
    formulas = []
    for term in terms:
        if term.expression and term.expression != term.canonical_name:
            formulas.append(f"{term.canonical_name} = {term.expression}")
    
    return QueryExplanation(
        tables_used=tables_used,
        filters_applied=filters_applied,
        assumptions=assumptions,
        formulas=formulas,
        business_terms=business_terms
    )


def _get_demo_sql(question: str):
    """Get demo SQL for common questions when OpenAI API is not configured."""
    from ..models.query import QueryResult
    import yaml
    import os
    
    question_lower = question.lower()
    
    # Load golden queries from YAML file
    try:
        golden_queries_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "golden_queries.yaml")
        with open(golden_queries_path, 'r', encoding='utf-8') as f:
            golden_data = yaml.safe_load(f)
        
        queries = golden_data.get('queries', [])
        
        # Find best matching query based on keywords
        best_match = None
        best_score = 0
        
        for query in queries:
            score = 0
            natural_lang = query.get('natural_language', '').lower()
            business_terms = query.get('business_terms', [])
            
            # Check for direct keyword matches
            for term in business_terms:
                if term.lower() in question_lower:
                    score += 2
            
            # Check for natural language similarity
            if any(word in question_lower for word in natural_lang.split()):
                score += 1
            
            # Check for specific patterns
            if "прибыль" in question_lower and "gross_profit" in business_terms:
                score += 3
            elif "выручка" in question_lower and "revenue" in business_terms:
                score += 3
            elif "товар" in question_lower and "product" in natural_lang:
                score += 3
            elif "магазин" in question_lower and "store" in business_terms:
                score += 3
            elif "регион" in question_lower and "region" in business_terms:
                score += 3
            elif "клиент" in question_lower and "customer" in business_terms:
                score += 3
            elif "конверсия" in question_lower and "conversion" in business_terms:
                score += 3
            
            if score > best_score:
                best_score = score
                best_match = query
        
        if best_match and best_score > 0:
            return QueryResult(
                data=[],  # Empty data for demo
                sql_query=best_match['expected_sql'].strip(),
                execution_time_ms=150 + (len(best_match['expected_sql']) // 10),
                row_count=len(best_match.get('expected_columns', [])),
                columns=best_match.get('expected_columns', []),
                confidence_score=0.9
            )
    
    except Exception as e:
        logger.warning(f"Could not load golden queries: {e}")
    
    # Fallback to simple keyword matching
    demo_queries = {
        "прибыль": {
            "sql": """
SELECT 
  DATE(s.order_date) AS day,
  SUM(s.revenue - s.cogs) AS gross_profit
FROM sales s
WHERE s.order_date >= current_date - INTERVAL '2 day'
  AND s.order_date < current_date
GROUP BY DATE(s.order_date)
ORDER BY day;
""",
            "columns": ["day", "gross_profit"]
        },
        "выручка": {
            "sql": """
SELECT 
  SUM(revenue) AS total_revenue
FROM sales
WHERE order_date >= date_trunc('month', current_date - interval '1 month')
  AND order_date < date_trunc('month', current_date);
""",
            "columns": ["total_revenue"]
        },
        "товар": {
            "sql": """
SELECT 
  p.sku,
  p.name,
  SUM(s.revenue) AS total_revenue
FROM sales s
JOIN products p ON s.product_id = p.product_id
WHERE s.order_date >= date_trunc('month', current_date)
  AND s.order_date < date_trunc('month', current_date) + interval '1 month'
GROUP BY p.sku, p.name
ORDER BY total_revenue DESC
LIMIT 10;
""",
            "columns": ["sku", "name", "total_revenue"]
        },
        "магазин": {
            "sql": """
SELECT 
  st.store_id,
  st.name,
  st.city,
  SUM(s.revenue) AS total_revenue
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY st.store_id, st.name, st.city
ORDER BY total_revenue DESC;
""",
            "columns": ["store_id", "name", "city", "total_revenue"]
        },
        "регион": {
            "sql": """
SELECT 
  st.region,
  COUNT(DISTINCT s.order_id) AS sales_count,
  SUM(s.revenue) AS total_revenue,
  COUNT(DISTINCT s.customer_id) AS unique_customers
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY st.region
ORDER BY total_revenue DESC;
""",
            "columns": ["region", "sales_count", "total_revenue", "unique_customers"]
        },
        "клиент": {
            "sql": """
SELECT 
  DATE(order_date) AS day,
  COUNT(DISTINCT customer_id) AS unique_customers,
  COUNT(*) AS total_orders
FROM orders
WHERE order_date >= current_date - INTERVAL '30 day'
  AND order_date < current_date
GROUP BY DATE(order_date)
ORDER BY day;
""",
            "columns": ["day", "unique_customers", "total_orders"]
        }
    }
    
    # Find matching demo query
    for keyword, query_data in demo_queries.items():
        if keyword in question_lower:
            return QueryResult(
                data=[],  # Empty data for demo
                sql_query=query_data["sql"].strip(),
                execution_time_ms=150,
                row_count=len(query_data["columns"]),
                columns=query_data["columns"],
                confidence_score=0.8
            )
    
    # Default demo query
    return QueryResult(
        data=[],  # Empty data for demo
        sql_query="""
SELECT 
  DATE(order_date) AS date,
  COUNT(*) AS order_count,
  SUM(revenue) AS total_revenue
FROM sales 
WHERE order_date >= current_date - INTERVAL '7 day'
GROUP BY DATE(order_date)
ORDER BY date;
""",
        execution_time_ms=120,
        row_count=7,
        columns=["date", "order_count", "total_revenue"],
        confidence_score=0.7
    )


def _generate_demo_explanation(question: str, sql: str) -> QueryExplanation:
    """Generate demo explanation for the query."""
    import re
    
    # Extract tables from SQL
    table_pattern = r'\bFROM\s+(\w+)|JOIN\s+(\w+)'
    tables_used = list(set([match[0] or match[1] for match in re.findall(table_pattern, sql, re.IGNORECASE)]))
    
    # Extract filters
    where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
    filters_applied = [where_match.group(1).strip()] if where_match else []
    
    # Generate assumptions based on SQL content
    assumptions = []
    if "current_date" in sql:
        assumptions.append("Использована текущая дата для временных фильтров")
    if "LIMIT" in sql:
        assumptions.append("Добавлено ограничение на количество строк")
    if "INTERVAL" in sql:
        assumptions.append("Применены временные интервалы для фильтрации данных")
    if "GROUP BY" in sql:
        assumptions.append("Данные сгруппированы для агрегации")
    if "JOIN" in sql:
        assumptions.append("Выполнено соединение таблиц")
    
    # Extract formulas
    formulas = []
    if "revenue - cogs" in sql:
        formulas.append("gross_profit = revenue - cogs")
    if "SUM(revenue)" in sql and "COUNT(*)" in sql:
        formulas.append("avg_order_value = total_revenue / order_count")
    if "NULLIF" in sql:
        formulas.append("Использована защита от деления на ноль")
    
    # Extract business terms from question
    business_terms = []
    question_lower = question.lower()
    if "прибыль" in question_lower:
        business_terms.append("gross_profit")
    if "выручка" in question_lower:
        business_terms.append("revenue")
    if "товар" in question_lower:
        business_terms.append("product")
    if "магазин" in question_lower:
        business_terms.append("store")
    if "регион" in question_lower:
        business_terms.append("region")
    if "клиент" in question_lower:
        business_terms.append("customer")
    if "конверсия" in question_lower:
        business_terms.append("conversion_rate")
    
    return QueryExplanation(
        tables_used=tables_used,
        filters_applied=filters_applied,
        assumptions=assumptions,
        formulas=formulas,
        business_terms=business_terms
    )