# BI-GPT Examples

## Примеры запросов на естественном языке

### Финансовые метрики

#### 1. Прибыль за последние 2 дня
**Запрос:** "Прибыль за последние 2 дня для всех магазинов"

**Ожидаемый SQL:**
```sql
SELECT 
  DATE(s.order_date) AS day,
  SUM(s.revenue - s.cogs) AS gross_profit
FROM sales s
WHERE s.order_date >= current_date - INTERVAL '2 day'
  AND s.order_date < current_date
GROUP BY DATE(s.order_date)
ORDER BY day;
```

**Объяснение:** Использована таблица sales. Прибыль = revenue - cogs. Период: последние 2 календарных дня.

#### 2. Маржинальность по регионам
**Запрос:** "Маржинальность за июль 2024 по регионам"

**Ожидаемый SQL:**
```sql
SELECT 
  st.region,
  SUM(s.revenue - s.cogs) / NULLIF(SUM(s.revenue), 0) * 100 AS gross_margin_pct
FROM sales s
JOIN stores st ON s.store_id = st.store_id
WHERE s.order_date >= '2024-07-01' 
  AND s.order_date < '2024-08-01'
GROUP BY st.region
ORDER BY gross_margin_pct DESC;
```

**Объяснение:** Маржинальность = (revenue - cogs)/revenue * 100; NULLIF для избежания деления на ноль.

#### 3. Выручка за прошлый месяц
**Запрос:** "Выручка за прошлый месяц"

**Ожидаемый SQL:**
```sql
SELECT 
  SUM(revenue) AS total_revenue
FROM sales
WHERE order_date >= date_trunc('month', current_date - interval '1 month')
  AND order_date < date_trunc('month', current_date);
```

### Товарные метрики

#### 4. Топ товаров по выручке
**Запрос:** "Топ 10 товаров по выручке за текущий месяц"

**Ожидаемый SQL:**
```sql
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
```

#### 5. Производительность по категориям
**Запрос:** "Производительность по категориям товаров за квартал"

**Ожидаемый SQL:**
```sql
SELECT 
  p.category,
  COUNT(DISTINCT s.order_id) AS order_count,
  SUM(s.revenue) AS total_revenue,
  AVG(s.revenue) AS avg_revenue_per_order
FROM sales s
JOIN products p ON s.product_id = p.product_id
WHERE s.order_date >= date_trunc('quarter', current_date)
  AND s.order_date < date_trunc('quarter', current_date) + interval '3 months'
GROUP BY p.category
ORDER BY total_revenue DESC;
```

### Локационные метрики

#### 6. Рейтинг магазинов
**Запрос:** "Рейтинг магазинов по выручке"

**Ожидаемый SQL:**
```sql
SELECT 
  st.store_id,
  st.name,
  st.city,
  SUM(s.revenue) AS total_revenue
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY st.store_id, st.name, st.city
ORDER BY total_revenue DESC;
```

#### 7. Сравнение регионов
**Запрос:** "Сравнение регионов по количеству продаж и выручке"

**Ожидаемый SQL:**
```sql
SELECT 
  st.region,
  COUNT(DISTINCT s.order_id) AS sales_count,
  SUM(s.revenue) AS total_revenue,
  COUNT(DISTINCT s.customer_id) AS unique_customers
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY st.region
ORDER BY total_revenue DESC;
```

### Клиентские метрики

#### 8. Активность клиентов
**Запрос:** "Активность клиентов по дням за последний месяц"

**Ожидаемый SQL:**
```sql
SELECT 
  DATE(order_date) AS day,
  COUNT(DISTINCT customer_id) AS unique_customers,
  COUNT(*) AS total_orders
FROM orders
WHERE order_date >= current_date - INTERVAL '30 day'
  AND order_date < current_date
GROUP BY DATE(order_date)
ORDER BY day;
```

### Сложные аналитические запросы

#### 9. Анализ прибыльности
**Запрос:** "Анализ прибыльности по товарам и регионам"

**Ожидаемый SQL:**
```sql
SELECT 
  p.category,
  st.region,
  COUNT(DISTINCT s.order_id) AS order_count,
  SUM(s.revenue) AS total_revenue,
  SUM(s.cogs) AS total_cogs,
  SUM(s.revenue - s.cogs) AS gross_profit,
  (SUM(s.revenue - s.cogs) / NULLIF(SUM(s.revenue), 0)) * 100 AS margin_pct
FROM sales s
JOIN products p ON s.product_id = p.product_id
JOIN stores st ON s.store_id = st.store_id
GROUP BY p.category, st.region
HAVING SUM(s.revenue) > 0
ORDER BY margin_pct DESC;
```

## API Примеры

### Запрос через API

```bash
curl -X POST "http://localhost:8000/api/v1/query/" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Прибыль за последние 2 дня",
    "user_id": "user123",
    "user_role": "manager",
    "max_rows": 1000
  }'
```

### Ответ API

```json
{
  "request_id": "uuid-here",
  "status": "completed",
  "result": {
    "data": [
      {"day": "2024-01-15", "gross_profit": 15000.50},
      {"day": "2024-01-16", "gross_profit": 18200.75}
    ],
    "columns": ["day", "gross_profit"],
    "row_count": 2,
    "execution_time_ms": 45.2,
    "sql_query": "SELECT DATE(order_date) AS day, SUM(revenue - cogs) AS gross_profit FROM sales WHERE order_date >= current_date - INTERVAL '2 day' GROUP BY DATE(order_date)",
    "confidence_score": 0.95
  },
  "explanation": {
    "tables_used": ["sales"],
    "filters_applied": ["order_date >= current_date - INTERVAL '2 day'"],
    "assumptions": ["Использована текущая дата для временных фильтров"],
    "formulas": ["gross_profit = revenue - cogs"],
    "business_terms": ["gross_profit"]
  }
}
```

### Валидация запроса

```bash
curl -X POST "http://localhost:8000/api/v1/query/validate" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Прибыль за последние 2 дня",
    "user_id": "user123",
    "user_role": "manager"
  }'
```

## Бизнес-термины

### Финансовые термины
- **gross_margin** (маржа) - `((revenue - cogs) / revenue) * 100`
- **gross_profit** (валовая прибыль) - `(revenue - cogs)`
- **revenue** (выручка) - `SUM(sales.revenue)`
- **average_check** (средний чек) - `AVG(order_total)`

### Временные периоды
- **last_week** (прошлая неделя) - `date_trunc('week', current_date - interval '1 week')`
- **last_month** (прошлый месяц) - `date_trunc('month', current_date - interval '1 month')`
- **current_month** (текущий месяц) - `date_trunc('month', current_date)`

### Товарные термины
- **sku** (артикул) - `products.sku`
- **product_category** (категория товара) - `products.category`

### Локационные термины
- **store** (магазин) - `stores.store_id`
- **region** (регион) - `stores.region`
- **city** (город) - `stores.city`

### Клиентские термины
- **customer_count** (количество клиентов) - `COUNT(DISTINCT customer_id)`

### Метрики продаж
- **sales_volume** (объем продаж) - `COUNT(*)`
- **conversion_rate** (конверсия) - `(completed_orders / total_orders) * 100`

## Безопасность

### Заблокированные операции
- `UPDATE`, `DELETE`, `INSERT`, `DROP`, `CREATE`, `ALTER`
- `COPY`, `UNLOAD`, `LOAD`
- `GRANT`, `REVOKE`, `DENY`
- `EXEC`, `EXECUTE`, `CALL`
- `pg_sleep`, `sleep`, `waitfor`
- Доступ к системным таблицам

### PII защита
Автоматически блокируются запросы к колонкам с PII:
- `customer_id` в таблицах `sales` и `orders`
- Другие персональные данные

### Предупреждения
- `SELECT *` - рекомендуется указывать конкретные колонки
- Большие `LIMIT` значения
- Множественные `JOIN`
- `ORDER BY` с числовыми индексами

## Мониторинг

### Метрики качества
- **exec_accuracy** - процент успешно выполненных запросов
- **aggregate_accuracy** - точность агрегатных вычислений
- **hallucination_rate** - процент запросов с несуществующими таблицами/колонками
- **self_service_rate** - процент запросов, решенных без участия аналитика
- **avg_response_time** - среднее время ответа
- **pii_incidents** - количество инцидентов с PII

### API для метрик
```bash
# Общие метрики
curl "http://localhost:8000/api/v1/metrics/overall"

# Метрики пользователя
curl "http://localhost:8000/api/v1/metrics/user/user123"

# Метрики безопасности
curl "http://localhost:8000/api/v1/metrics/security"

# Производительность
curl "http://localhost:8000/api/v1/metrics/performance"

# Дашборд
curl "http://localhost:8000/api/v1/metrics/dashboard"
```