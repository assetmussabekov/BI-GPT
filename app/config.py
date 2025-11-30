"""Configuration settings for BI-GPT application."""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/bi_gpt_db"
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your_secret_key_here"
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Query limits
    max_query_rows: int = 1000000
    query_timeout_seconds: int = 30
    max_query_cost: int = 1000
    
    # Monitoring
    prometheus_port: int = 8001
    log_level: str = "INFO"
    
    # Business glossary
    glossary_path: str = "data/business_glossary.yaml"
    schema_path: str = "data/schema.yaml"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
