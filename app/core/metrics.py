"""Metrics collection for BI-GPT."""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query."""
    request_id: str
    user_id: str
    question: str
    sql_generated: bool
    sql_executed: bool
    execution_time_ms: float
    row_count: int
    confidence_score: float
    security_level: str
    pii_detected: bool
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Collects and aggregates metrics for BI-GPT."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize metrics collector."""
        self.max_history = max_history
        self.query_history: deque = deque(maxlen=max_history)
        self.user_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "pii_incidents": 0,
            "total_execution_time": 0.0,
            "avg_confidence": 0.0
        })
        self.hourly_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "queries_count": 0,
            "success_rate": 0.0,
            "avg_execution_time": 0.0,
            "pii_incidents": 0
        })
    
    def record_query(self, metrics: QueryMetrics) -> None:
        """Record query metrics."""
        self.query_history.append(metrics)
        
        # Update user metrics
        user_id = metrics.user_id
        self.user_metrics[user_id]["total_queries"] += 1
        
        if metrics.sql_executed and not metrics.error_message:
            self.user_metrics[user_id]["successful_queries"] += 1
        else:
            self.user_metrics[user_id]["failed_queries"] += 1
        
        if metrics.pii_detected:
            self.user_metrics[user_id]["pii_incidents"] += 1
        
        self.user_metrics[user_id]["total_execution_time"] += metrics.execution_time_ms
        
        # Update average confidence
        current_avg = self.user_metrics[user_id]["avg_confidence"]
        total_queries = self.user_metrics[user_id]["total_queries"]
        self.user_metrics[user_id]["avg_confidence"] = (
            (current_avg * (total_queries - 1) + metrics.confidence_score) / total_queries
        )
        
        # Update hourly stats
        hour_key = metrics.timestamp.strftime("%Y-%m-%d-%H")
        self.hourly_stats[hour_key]["queries_count"] += 1
        
        if metrics.sql_executed and not metrics.error_message:
            self.hourly_stats[hour_key]["success_rate"] = (
                self.hourly_stats[hour_key]["success_rate"] * 
                (self.hourly_stats[hour_key]["queries_count"] - 1) + 1.0
            ) / self.hourly_stats[hour_key]["queries_count"]
        
        if metrics.pii_detected:
            self.hourly_stats[hour_key]["pii_incidents"] += 1
        
        # Update average execution time
        current_avg_time = self.hourly_stats[hour_key]["avg_execution_time"]
        queries_count = self.hourly_stats[hour_key]["queries_count"]
        self.hourly_stats[hour_key]["avg_execution_time"] = (
            (current_avg_time * (queries_count - 1) + metrics.execution_time_ms) / queries_count
        )
    
    def get_overall_metrics(self) -> Dict[str, Any]:
        """Get overall system metrics."""
        if not self.query_history:
            return {
                "total_queries": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "avg_confidence": 0.0,
                "pii_incidents": 0,
                "active_users": 0
            }
        
        total_queries = len(self.query_history)
        successful_queries = sum(1 for q in self.query_history if q.sql_executed and not q.error_message)
        pii_incidents = sum(1 for q in self.query_history if q.pii_detected)
        total_execution_time = sum(q.execution_time_ms for q in self.query_history)
        total_confidence = sum(q.confidence_score for q in self.query_history)
        active_users = len(self.user_metrics)
        
        return {
            "total_queries": total_queries,
            "success_rate": successful_queries / total_queries if total_queries > 0 else 0.0,
            "avg_execution_time": total_execution_time / total_queries if total_queries > 0 else 0.0,
            "avg_confidence": total_confidence / total_queries if total_queries > 0 else 0.0,
            "pii_incidents": pii_incidents,
            "active_users": active_users
        }
    
    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get metrics for specific user."""
        return self.user_metrics.get(user_id, {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "pii_incidents": 0,
            "total_execution_time": 0.0,
            "avg_confidence": 0.0
        })
    
    def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly statistics for last N hours."""
        now = datetime.utcnow()
        stats = []
        
        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            
            stats.append({
                "hour": hour_key,
                "queries_count": self.hourly_stats[hour_key]["queries_count"],
                "success_rate": self.hourly_stats[hour_key]["success_rate"],
                "avg_execution_time": self.hourly_stats[hour_key]["avg_execution_time"],
                "pii_incidents": self.hourly_stats[hour_key]["pii_incidents"]
            })
        
        return list(reversed(stats))
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent queries."""
        recent = list(self.query_history)[-limit:]
        return [
            {
                "request_id": q.request_id,
                "user_id": q.user_id,
                "question": q.question[:100] + "..." if len(q.question) > 100 else q.question,
                "execution_time_ms": q.execution_time_ms,
                "confidence_score": q.confidence_score,
                "success": q.sql_executed and not q.error_message,
                "timestamp": q.timestamp.isoformat()
            }
            for q in recent
        ]
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security-related metrics."""
        if not self.query_history:
            return {
                "total_queries": 0,
                "pii_incidents": 0,
                "security_violations": 0,
                "blocked_queries": 0
            }
        
        total_queries = len(self.query_history)
        pii_incidents = sum(1 for q in self.query_history if q.pii_detected)
        security_violations = sum(1 for q in self.query_history if q.security_level in ["dangerous", "blocked"])
        blocked_queries = sum(1 for q in self.query_history if q.security_level == "blocked")
        
        return {
            "total_queries": total_queries,
            "pii_incidents": pii_incidents,
            "security_violations": security_violations,
            "blocked_queries": blocked_queries,
            "pii_incident_rate": pii_incidents / total_queries if total_queries > 0 else 0.0,
            "security_violation_rate": security_violations / total_queries if total_queries > 0 else 0.0
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        if not self.query_history:
            return {
                "avg_execution_time": 0.0,
                "p95_execution_time": 0.0,
                "p99_execution_time": 0.0,
                "slow_queries_count": 0
            }
        
        execution_times = [q.execution_time_ms for q in self.query_history if q.sql_executed]
        
        if not execution_times:
            return {
                "avg_execution_time": 0.0,
                "p95_execution_time": 0.0,
                "p99_execution_time": 0.0,
                "slow_queries_count": 0
            }
        
        execution_times.sort()
        n = len(execution_times)
        
        return {
            "avg_execution_time": sum(execution_times) / n,
            "p95_execution_time": execution_times[int(0.95 * n)] if n > 0 else 0.0,
            "p99_execution_time": execution_times[int(0.99 * n)] if n > 0 else 0.0,
            "slow_queries_count": sum(1 for t in execution_times if t > 5000)  # > 5 seconds
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()