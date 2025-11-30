#!/usr/bin/env python3
"""Simple demo script for BI-GPT without external dependencies."""

import json
from pathlib import Path


def load_glossary():
    """Load glossary from YAML file."""
    glossary_path = Path(__file__).parent / "data" / "business_glossary.yaml"
    
    # Simple YAML parser for demo
    with open(glossary_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract basic info
    lines = content.split('\n')
    terms = []
    tables = []
    
    in_terms = False
    in_tables = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('terms:'):
            in_terms = True
            in_tables = False
        elif line.startswith('table_mappings:'):
            in_terms = False
            in_tables = True
        elif in_terms and line.startswith('- name:') and 'canonical_name:' in line:
            # Extract term name
            if 'canonical_name:' in line:
                term_name = line.split('canonical_name:')[1].strip().strip('"')
                terms.append(term_name)
        elif in_tables and line.startswith('sales:') or line.startswith('products:') or line.startswith('stores:') or line.startswith('orders:'):
            table_name = line.split(':')[0]
            tables.append(table_name)
    
    return terms, tables


def demo_business_terms():
    """Demo business terms functionality."""
    print("🚀 BI-GPT Simple Demo")
    print("=" * 50)
    
    print("📚 Loading business glossary...")
    terms, tables = load_glossary()
    
    print(f"✅ Found {len(terms)} business terms:")
    for term in terms[:10]:  # Show first 10
        print(f"  - {term}")
    if len(terms) > 10:
        print(f"  ... and {len(terms) - 10} more")
    
    print(f"\n🗄️  Found {len(tables)} database tables:")
    for table in tables:
        print(f"  - {table}")
    
    print("\n📊 Example Business Terms:")
    examples = {
        "gross_margin": "Маржа = ((revenue - cogs) / revenue) * 100",
        "gross_profit": "Валовая прибыль = revenue - cogs", 
        "revenue": "Выручка = SUM(sales.revenue)",
        "average_check": "Средний чек = AVG(order_total)",
        "sku": "Артикул товара = products.sku",
        "region": "Регион = stores.region"
    }
    
    for term, formula in examples.items():
        print(f"  {term}: {formula}")
    
    print("\n🔍 Example Natural Language Queries:")
    example_queries = [
        "Прибыль за последние 2 дня для всех магазинов",
        "Маржинальность за июль 2024 по регионам", 
        "Топ 10 товаров по выручке за текущий месяц",
        "Средний чек по дням за последнюю неделю",
        "Рейтинг магазинов по выручке",
        "Активность клиентов по дням за последний месяц"
    ]
    
    for i, query in enumerate(example_queries, 1):
        print(f"  {i}. {query}")
    
    print("\n🔒 Security Features:")
    security_features = [
        "✅ Only SELECT queries allowed",
        "✅ PII columns automatically blocked",
        "✅ Dangerous operations (UPDATE, DELETE) blocked",
        "✅ System tables access blocked",
        "✅ Query cost estimation and limits",
        "✅ Automatic LIMIT addition for large results"
    ]
    
    for feature in security_features:
        print(f"  {feature}")
    
    print("\n📈 Monitoring & Metrics:")
    metrics = [
        "Query execution accuracy",
        "Response time tracking", 
        "PII incident detection",
        "User activity monitoring",
        "Security violation alerts",
        "Business term usage statistics"
    ]
    
    for metric in metrics:
        print(f"  - {metric}")
    
    print("\n🎯 Example SQL Generation:")
    print("Input: 'Прибыль за последние 2 дня'")
    print("Output:")
    example_sql = """
    SELECT 
      DATE(s.order_date) AS day,
      SUM(s.revenue - s.cogs) AS gross_profit
    FROM sales s
    WHERE s.order_date >= current_date - INTERVAL '2 day'
      AND s.order_date < current_date
    GROUP BY DATE(s.order_date)
    ORDER BY day;
    """
    print(example_sql)
    
    print("Explanation:")
    print("  - Tables used: sales")
    print("  - Business terms: gross_profit")
    print("  - Formula: gross_profit = revenue - cogs")
    print("  - Time filter: last 2 calendar days")
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\n🚀 To run the full application:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Set up database connection in config.py")
    print("3. Add OpenAI API key to environment")
    print("4. Run: uvicorn app.main:app --reload")
    print("5. Visit: http://localhost:8000/docs")


if __name__ == "__main__":
    demo_business_terms()