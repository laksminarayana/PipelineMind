import pytest
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.database.schema import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_retain_and_recall_incident():
    incident = {
        "incident_id": "TEST-INC-999",
        "deployment_id": "dep-test-999",
        "pipeline_stage": "health_verification",
        "error_message": "Postgres timeout connection refused at 5432",
        "root_cause": "Missing db-secret environment variables",
        "infrastructure_changes": "Changed DB_HOST to postgres-cluster",
        "corrective_action": "Injected secretKeyRef db-secret",
        "fix_succeeded": True
    }

    retention = memory_manager.retain_incident(incident)
    assert retention["status"] == "success"

    # Recall
    results = memory_manager.recall_similar_incidents("postgres timeout connection 5432")
    assert len(results) > 0
    assert any("TEST-INC-999" in r.get("content", "") for r in results)


def test_memory_reflection():
    reflection = memory_manager.reflect_on_incident("postgres database connection timeout")
    assert "synthesis" in reflection
    assert reflection["confidence"] > 0.0
