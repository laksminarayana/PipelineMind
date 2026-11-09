import random
import time
from typing import Dict, Any, List
from datetime import datetime, timezone
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from backend.app.database.connection import get_db

# Prometheus Metrics Definitions
PROMETHEUS_DEPLOYMENTS_TOTAL = Counter(
    "pipelinemind_deployments_total",
    "Completed pipeline deployment outcomes",
    ["status", "strategy"]
)
PROMETHEUS_PIPELINE_DURATION_SECONDS = Histogram(
    "pipelinemind_pipeline_duration_seconds",
    "Pipeline execution duration in seconds",
    buckets=[1, 2, 5, 10, 30, 60]
)
PROMETHEUS_INCIDENTS_TOTAL = Counter(
    "pipelinemind_incidents_total",
    "Total incidents detected",
    ["stage"]
)
PROMETHEUS_MEMORY_RECORDS_GAUGE = Gauge(
    "pipelinemind_hindsight_memories_total",
    "Total memories stored in Hindsight memory bank"
)
PROMETHEUS_HTTP_LATENCY = Histogram(
    "pipelinemind_http_request_duration_seconds",
    "HTTP request latency seconds",
    ["endpoint"]
)


class MetricsService:
    """
    Supplies Prometheus telemetry and dashboard metrics.
    """

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        with get_db() as conn:
            # Deployment counts
            cursor = conn.execute("SELECT COUNT(*) FROM deployments")
            total_deployments = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM deployments WHERE status = 'SUCCESS'")
            successful_deployments = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM deployments WHERE status = 'FAILED'")
            failed_deployments = cursor.fetchone()[0]

            # Incidents count
            cursor = conn.execute("SELECT COUNT(*) FROM incidents")
            recorded_incidents = cursor.fetchone()[0]

            # Hindsight memories count
            cursor = conn.execute("SELECT COUNT(*) FROM hindsight_memories")
            memory_records = cursor.fetchone()[0]

        # Calculate success percentage
        success_rate = (
            round((successful_deployments / max(1, total_deployments)) * 100, 1)
            if total_deployments > 0
            else 100.0
        )

        # Dynamic realistic telemetry
        cpu_usage = round(28.5 + (random.random() * 8.0), 1)
        memory_usage = round(44.2 + (random.random() * 5.0), 1)
        api_latency_ms = round(14.8 + (random.random() * 6.0), 1)
        error_rate_pct = round(0.04 + (random.random() * 0.05), 3)

        # Pod statuses
        pods = [
            {"name": "order-processor-78d9f4-k2x9", "ready": "1/1", "status": "Running", "restarts": 0, "age": "4d12h", "cpu": "42m", "mem": "184Mi"},
            {"name": "order-processor-78d9f4-p9z1", "ready": "1/1", "status": "Running", "restarts": 0, "age": "4d12h", "cpu": "38m", "mem": "178Mi"},
            {"name": "order-processor-78d9f4-l5q4", "ready": "1/1", "status": "Running", "restarts": 0, "age": "4d12h", "cpu": "45m", "mem": "192Mi"},
            {"name": "hindsight-memory-bank-0", "ready": "1/1", "status": "Running", "restarts": 0, "age": "18d", "cpu": "65m", "mem": "310Mi"},
            {"name": "prometheus-server-5f9cb8-b11w", "ready": "1/1", "status": "Running", "restarts": 0, "age": "12d", "cpu": "52m", "mem": "240Mi"}
        ]

        # Latency timeseries for Recharts
        latency_series = [
            {"time": "12:00", "latency": 15.2, "error_rate": 0.02},
            {"time": "12:10", "latency": 16.1, "error_rate": 0.03},
            {"time": "12:20", "latency": 14.8, "error_rate": 0.02},
            {"time": "12:30", "latency": 38.5, "error_rate": 2.10},  # incident spike
            {"time": "12:40", "latency": 15.4, "error_rate": 0.04},
            {"time": "12:50", "latency": 14.2, "error_rate": 0.01},
        ]

        # Update prometheus gauge
        PROMETHEUS_MEMORY_RECORDS_GAUGE.set(memory_records)

        return {
            "total_deployments": total_deployments,
            "successful_deployments": successful_deployments,
            "failed_deployments": failed_deployments,
            "deployment_success_percentage": success_rate,
            "recorded_incidents": recorded_incidents,
            "hindsight_memory_records": memory_records,
            "application_health": "Healthy" if failed_deployments <= 2 else "Degraded",
            "cpu_usage_pct": cpu_usage,
            "memory_usage_pct": memory_usage,
            "api_latency_ms": api_latency_ms,
            "http_error_rate_pct": error_rate_pct,
            "active_pods": pods,
            "latency_trend": latency_series,
            "telemetry_source": "Simulated demonstration telemetry"
        }

    @staticmethod
    def get_prometheus_payload() -> bytes:
        with get_db() as conn:
            memory_records = conn.execute(
                "SELECT COUNT(*) FROM hindsight_memories"
            ).fetchone()[0]
        PROMETHEUS_MEMORY_RECORDS_GAUGE.set(memory_records)
        return generate_latest()


metrics_service = MetricsService()
