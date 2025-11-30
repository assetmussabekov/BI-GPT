# BI-GPT Deployment Guide

## 🚀 Развертывание в продакшене

### 1. Подготовка окружения

#### Системные требования
- Python 3.8+
- PostgreSQL 12+
- Redis (опционально, для кеширования)
- 2GB+ RAM
- 1GB+ свободного места

#### Установка зависимостей
```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка базы данных

#### PostgreSQL
```sql
-- Создание базы данных
CREATE DATABASE bi_gpt_db;

-- Создание пользователя
CREATE USER bi_gpt_user WITH PASSWORD 'secure_password';

-- Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE bi_gpt_db TO bi_gpt_user;

-- Создание схемы для тестовых данных
CREATE SCHEMA analytics;
GRANT ALL ON SCHEMA analytics TO bi_gpt_user;
```

#### Создание тестовых таблиц
```sql
-- Таблица продаж
CREATE TABLE analytics.sales (
    order_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    revenue DECIMAL(10,2) NOT NULL,
    cogs DECIMAL(10,2) NOT NULL,
    quantity INTEGER NOT NULL
);

-- Справочник товаров
CREATE TABLE analytics.products (
    product_id INTEGER PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

-- Справочник магазинов
CREATE TABLE analytics.stores (
    store_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    address TEXT
);

-- Таблица заказов
CREATE TABLE analytics.orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,
    order_total DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) NOT NULL
);

-- Индексы для производительности
CREATE INDEX idx_sales_date ON analytics.sales(order_date);
CREATE INDEX idx_sales_store ON analytics.sales(store_id);
CREATE INDEX idx_sales_product ON analytics.sales(product_id);
```

### 3. Конфигурация

#### Переменные окружения
```bash
# .env файл
DATABASE_URL=postgresql://bi_gpt_user:secure_password@localhost:5432/bi_gpt_db
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your_secret_key_here
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
MAX_QUERY_ROWS=1000000
QUERY_TIMEOUT_SECONDS=30
MAX_QUERY_COST=1000
PROMETHEUS_PORT=8001
LOG_LEVEL=INFO
```

#### Настройка безопасности
```python
# config.py - дополнительные настройки для продакшена
class ProductionSettings(Settings):
    # Более строгие лимиты
    max_query_rows: int = 100000
    query_timeout_seconds: int = 15
    max_query_cost: int = 500
    
    # Безопасность
    allowed_origins: List[str] = ["https://yourdomain.com"]
    
    # Логирование
    log_level: str = "WARNING"
    
    # Мониторинг
    enable_metrics: bool = True
    metrics_retention_days: int = 30
```

### 4. Развертывание с Docker

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование и установка Python зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Создание пользователя
RUN useradd --create-home --shell /bin/bash app
USER app

# Экспорт порта
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  bi-gpt:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://bi_gpt_user:secure_password@postgres:5432/bi_gpt_db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=bi_gpt_db
      - POSTGRES_USER=bi_gpt_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - bi-gpt

volumes:
  postgres_data:
```

### 5. Nginx конфигурация

#### nginx.conf
```nginx
events {
    worker_connections 1024;
}

http {
    upstream bi_gpt {
        server bi-gpt:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Безопасность
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # Rate limiting
        limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

        location / {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://bi_gpt;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Статические файлы
        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### 6. Мониторинг и логирование

#### Prometheus конфигурация
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bi-gpt'
    static_configs:
      - targets: ['bi-gpt:8001']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

#### Grafana дашборд
```json
{
  "dashboard": {
    "title": "BI-GPT Metrics",
    "panels": [
      {
        "title": "Query Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(bi_gpt_queries_total{status=\"completed\"}[5m]) / rate(bi_gpt_queries_total[5m]) * 100"
          }
        ]
      },
      {
        "title": "Average Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(bi_gpt_query_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "PII Incidents",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(bi_gpt_pii_incidents_total[1h])"
          }
        ]
      }
    ]
  }
}
```

### 7. Backup и восстановление

#### Backup скрипт
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="bi_gpt_db"

# Backup базы данных
pg_dump $DATABASE_URL > $BACKUP_DIR/db_backup_$DATE.sql

# Backup конфигурации
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz data/ config.py

# Очистка старых backup'ов (старше 30 дней)
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

#### Восстановление
```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1
DB_NAME="bi_gpt_db"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Восстановление базы данных
psql $DATABASE_URL < $BACKUP_FILE

echo "Database restored from: $BACKUP_FILE"
```

### 8. CI/CD Pipeline

#### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy BI-GPT

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: pytest tests/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to production
        run: |
          # Ваши команды развертывания
          docker-compose up -d --build
```

### 9. Безопасность в продакшене

#### Рекомендации
1. **HTTPS только** - все соединения должны быть зашифрованы
2. **API ключи** - храните в переменных окружения, не в коде
3. **Rate limiting** - ограничьте количество запросов от одного IP
4. **Логирование** - ведите детальные логи всех операций
5. **Мониторинг** - настройте алерты на подозрительную активность
6. **Backup** - регулярные резервные копии данных
7. **Обновления** - регулярно обновляйте зависимости

#### Проверка безопасности
```bash
# Проверка уязвимостей в зависимостях
pip install safety
safety check

# Сканирование кода
pip install bandit
bandit -r app/

# Проверка конфигурации
python -c "from app.config import settings; print('Config loaded successfully')"
```

### 10. Масштабирование

#### Горизонтальное масштабирование
```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  bi-gpt:
    build: .
    deploy:
      replicas: 3
    environment:
      - DATABASE_URL=postgresql://bi_gpt_user:secure_password@postgres:5432/bi_gpt_db
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.load_balancer.conf:/etc/nginx/nginx.conf
    depends_on:
      - bi-gpt
```

#### Load balancer конфигурация
```nginx
upstream bi_gpt {
    least_conn;
    server bi-gpt_1:8000;
    server bi-gpt_2:8000;
    server bi-gpt_3:8000;
}
```

### 11. Troubleshooting

#### Частые проблемы
1. **Ошибки подключения к БД** - проверьте DATABASE_URL
2. **Медленные запросы** - оптимизируйте индексы
3. **Высокое потребление памяти** - увеличьте лимиты или оптимизируйте запросы
4. **Ошибки OpenAI API** - проверьте API ключ и лимиты

#### Логи для диагностики
```bash
# Логи приложения
docker-compose logs -f bi-gpt

# Логи базы данных
docker-compose logs -f postgres

# Метрики производительности
curl http://localhost:8001/metrics
```

Этот гайд поможет вам развернуть BI-GPT в продакшене с учетом всех аспектов безопасности, мониторинга и масштабирования.