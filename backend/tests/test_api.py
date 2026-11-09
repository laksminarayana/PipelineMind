import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.schema import init_db, seed_initial_data_if_empty


@pytest.fixture(autouse=True)
def setup_app():
    init_db()
    seed_initial_data_if_empty()


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "hindsight_memory" in data


def test_deployments_crud():
    # Create deployment
    payload = {
        "service_name": "order-processing-service",
        "environment": "production",
        "branch": "main",
        "commit_sha": "abc1234",
        "commit_message": "Automated unit test deployment",
        "author": "Tester <test@company.io>",
        "strategy": "rolling"
    }
    create_res = client.post("/api/deployments", json=payload)
    assert create_res.status_code == 201
    dep_data = create_res.json()
    assert dep_data["commit_sha"] == "abc1234"

    # List deployments
    list_res = client.get("/api/deployments")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


def test_metrics():
    res = client.get("/api/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "total_deployments" in data
    assert "deployment_success_percentage" in data
    assert "hindsight_memory_records" in data


def test_prometheus_export():
    response = client.get("/api/prometheus")
    assert response.status_code == 200
    assert "pipelinemind_hindsight_memories_total" in response.text
    assert "pipelinemind_http_request_duration_seconds" in response.text


def test_demo_step_1():
    res = client.post("/api/demo/run-step", json={"step": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["step"] == 1
    assert data["hindsight_learned"] is True
    assert "incident" in data


def test_demo_memory_learning_sequence():
    client.post("/api/demo/reset")

    first = client.post("/api/demo/run-step", json={"step": 1})
    assert first.status_code == 200
    assert first.json()["hindsight_learned"] is True

    second = client.post("/api/demo/run-step", json={"step": 2})
    assert second.status_code == 200
    step_two = second.json()
    assert step_two["similarity_detected"] is True
    assert step_two["recalled_memories"]
    assert step_two["risk_analysis"]["related_incidents"]
    assert "94%" not in step_two["agent_recommendation"]

    third = client.post("/api/demo/run-step", json={"step": 3})
    assert third.status_code == 200
    step_three = third.json()
    assert step_three["pipeline_run"]["status"] == "success"
    assert step_three["learning_improvement"]["after_hindsight"]["deployment_3_outcome"] == "Pipeline succeeded"
