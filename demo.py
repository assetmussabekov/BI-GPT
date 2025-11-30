#!/usr/bin/env python3
"""Demo script for BI-GPT."""

import asyncio
import json
from typing import Dict, Any

from app.services.glossary_service import GlossaryService
from app.services.sql_generator import SQLGenerator
from app.services.security_service import SecurityService
from app.models.query import QueryRequest


async def demo_basic_functionality():
    """Demonstrate basic BI-GPT functionality."""
    print("🚀 BI-GPT Demo")
    print("=" * 50)
    
    # Initialize services
    print("📚 Loading business glossary...")
    glossary_service = GlossaryService()
    glossary = glossary_service.get_glossary()
    print(f"✅ Loaded glossary v{glossary.version} with {len(glossary.terms)} terms")
    
    print("\n🔧 Initializing services...")
    sql_generator = SQLGenerator(glossary)
    security_service = SecurityService(glossary)
    print("✅ Services initialized")
    
    # Demo queries
    demo_queries = [
        "Прибыль за последние 2 дня для всех магазинов",
        "Маржинальность за июль 2024 по регионам",
        "Топ 10 товаров по выручке за текущий месяц",
        "Средний чек по дням за последнюю неделю"
    ]
    
    print(f"\n📊 Running {len(demo_queries)} demo queries...")
    print("=" * 50)
    
    for i, question in enumerate(demo_queries, 1):
        print(f"\n🔍 Query {i}: {question}")
        print("-" * 40)
        
        try:
            # Create request
            request = QueryRequest(
                question=question,
                user_id="demo_user",
                user_role="manager"
            )
            
            # Extract business terms
            terms = glossary_service.extract_business_terms(question)
            print(f"📝 Business terms found: {[term.canonical_name for term in terms]}")
            
            # Generate SQL (mock - since we don't have OpenAI API key in demo)
            print("🤖 Generating SQL...")
            print("⚠️  Note: This is a demo - actual SQL generation requires OpenAI API key")
            
            # Show expected SQL from golden queries
            if i == 1:
                expected_sql = """
                SELECT 
                  DATE(s.order_date) AS day,
                  SUM(s.revenue - s.cogs) AS gross_profit
                FROM sales s
                WHERE s.order_date >= current_date - INTERVAL '2 day'
                  AND s.order_date < current_date
                GROUP BY DATE(s.order_date)
                ORDER BY day;
                """
                print(f"📋 Expected SQL:\n{expected_sql.strip()}")
            
            # Security check (using expected SQL)
            if i == 1:
                security_check = security_service.check_query_security(expected_sql.strip())
                print(f"🔒 Security check: {security_check.level}")
                print(f"✅ Safe to execute: {security_check.is_safe}")
                if security_check.warnings:
                    print(f"⚠️  Warnings: {security_check.warnings}")
            
            print("✅ Query processed successfully")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\n📈 Available metrics:")
    print("  - Business terms: Financial, Product, Location, Customer, Sales, Time")
    print("  - Security levels: Safe, Warning, Dangerous, Blocked")
    print("  - PII protection: Automatic detection and blocking")
    print("  - Query validation: Syntax, security, and business logic checks")


def demo_glossary_exploration():
    """Demonstrate glossary exploration."""
    print("\n🔍 Business Glossary Exploration")
    print("=" * 50)
    
    glossary_service = GlossaryService()
    glossary = glossary_service.get_glossary()
    
    # Show categories
    categories = {}
    for term in glossary.terms.values():
        category = term.category.value
        if category not in categories:
            categories[category] = []
        categories[category].append(term.canonical_name)
    
    print("📚 Available business term categories:")
    for category, terms in categories.items():
        print(f"  {category}: {len(terms)} terms")
        for term in terms[:3]:  # Show first 3 terms
            print(f"    - {term}")
        if len(terms) > 3:
            print(f"    ... and {len(terms) - 3} more")
    
    # Show table mappings
    print(f"\n🗄️  Available tables: {len(glossary.table_mappings)}")
    for table_name, table_mapping in glossary.table_mappings.items():
        print(f"  {table_name}: {len(table_mapping.columns)} columns")
        pii_columns = [col.name for col in table_mapping.columns if col.is_pii]
        if pii_columns:
            print(f"    PII columns: {pii_columns}")
    
    # Show PII protection
    pii_columns = glossary.get_pii_columns()
    print(f"\n🔒 PII Protection: {len(pii_columns)} protected columns")
    for pii_col in pii_columns[:5]:  # Show first 5
        print(f"  - {pii_col}")
    if len(pii_columns) > 5:
        print(f"  ... and {len(pii_columns) - 5} more")


def demo_security_features():
    """Demonstrate security features."""
    print("\n🔒 Security Features Demo")
    print("=" * 50)
    
    glossary_service = GlossaryService()
    glossary = glossary_service.get_glossary()
    security_service = SecurityService(glossary)
    
    # Test queries
    test_queries = [
        ("SELECT SUM(revenue) FROM sales", "Safe query"),
        ("SELECT * FROM sales", "Warning: SELECT *"),
        ("SELECT customer_id FROM sales", "PII access detected"),
        ("UPDATE sales SET revenue = 0", "Dangerous: UPDATE"),
        ("DELETE FROM sales", "Blocked: DELETE"),
        ("SELECT * FROM pg_catalog.pg_user", "Blocked: system table")
    ]
    
    for sql, description in test_queries:
        print(f"\n🧪 Testing: {description}")
        print(f"SQL: {sql}")
        
        security_check = security_service.check_query_security(sql)
        print(f"Result: {security_check.level}")
        print(f"Safe: {security_check.is_safe}")
        print(f"PII: {security_check.pii_flag}")
        
        if security_check.blocked_operations:
            print(f"Blocked operations: {security_check.blocked_operations}")
        if security_check.warnings:
            print(f"Warnings: {security_check.warnings}")


if __name__ == "__main__":
    print("🎯 BI-GPT Demonstration")
    print("This demo shows the core functionality of BI-GPT")
    print("without requiring database or OpenAI API connections.\n")
    
    # Run demos
    asyncio.run(demo_basic_functionality())
    demo_glossary_exploration()
    demo_security_features()
    
    print("\n🚀 To run the full application:")
    print("1. Set up your database connection in config.py")
    print("2. Add your OpenAI API key to environment variables")
    print("3. Run: uvicorn app.main:app --reload")
    print("4. Visit: http://localhost:8000/docs")