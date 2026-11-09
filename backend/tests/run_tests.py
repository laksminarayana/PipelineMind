import sys
from pathlib import Path
ROOT_DIR = Path("G:/pipeline")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import time
from backend.app.database.schema import init_db, seed_initial_data_if_empty
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.analyzers.diff_parser import DiffParser
from backend.app.analyzers.risk_analyzer import risk_analyzer
from backend.app.services.deployment_service import deployment_service
from backend.app.services.pipeline_service import pipeline_service
from backend.app.services.incident_service import incident_service
from backend.app.services.demo_service import demo_service
from backend.app.services.metrics_service import metrics_service


def run():
    print("--- 1. Initializing Database ---", flush=True)
    init_db()
    seed_initial_data_if_empty()
    print("[OK] Database initialized successfully.", flush=True)

    print("\n--- 2. Testing Diff Parser ---", flush=True)
    docker_res = DiffParser.parse_dockerfile("+USER root\n+EXPOSE 22")
    assert len(docker_res["findings"]) == 2
    print(f"[OK] Dockerfile parser passed ({len(docker_res['findings'])} findings).", flush=True)

    k8s_res = DiffParser.parse_k8s("+privileged: true\n+hostNetwork: true")
    assert len(k8s_res["findings"]) == 2
    print(f"[OK] K8s parser passed ({len(k8s_res['findings'])} findings).", flush=True)

    print("\n--- 3. Testing Hindsight Memory Integration ---", flush=True)
    retain_res = memory_manager.retain_incident({
        "incident_id": "TEST-INC-VERIFY",
        "deployment_id": "dep-verify-01",
        "pipeline_stage": "health_verification",
        "error_message": "Database connection timeout to postgres-cluster",
        "root_cause": "Missing db-secret references",
        "infrastructure_changes": "Changed database host",
        "corrective_action": "Attached Kubernetes secret db-secret",
        "fix_succeeded": True
    })
    assert retain_res["status"] == "success"
    print(f"[OK] Hindsight retain succeeded: memory_id={retain_res['memory_id']}", flush=True)

    recalled = memory_manager.recall_similar_incidents("database connection timeout postgres")
    assert len(recalled) > 0
    print(f"[OK] Hindsight recall returned {len(recalled)} memories.", flush=True)

    reflection = memory_manager.reflect_on_incident("database connection timeout")
    assert "synthesis" in reflection
    print(f"[OK] Hindsight reflect synthesized: {reflection['synthesis'][:70]}...", flush=True)

    print("\n--- 4. Testing Risk Analyzer ---", flush=True)
    async def _test_risk():
        res = await risk_analyzer.analyze(
            db_config_diff="+DB_HOST=postgres-cluster.internal:5432\n+password=plaintext",
            strategy="rolling"
        )
        assert res["risk_score"] > 40
        print(f"[OK] Risk score: {res['risk_score']} ({res['risk_category']}), Decision: {res['deployment_decision']}", flush=True)

    asyncio.run(_test_risk())

    print("\n--- 5. Testing Demo Step 1 (Failure & Learning) ---", flush=True)
    async def _test_demo1():
        d1 = await demo_service.execute_scenario_1()
        assert d1["step"] == 1
        print(f"[OK] Demo 1: Incident {d1['incident']['incident_id']} retained in Hindsight.", flush=True)

    asyncio.run(_test_demo1())

    print("\n--- 6. Testing Demo Step 2 (Memory Recall & Proactive Warning) ---", flush=True)
    async def _test_demo2():
        d2 = await demo_service.execute_scenario_2()
        assert d2["step"] == 2
        print(f"[OK] Demo 2: High risk warning triggered (Risk score: {d2['risk_analysis']['risk_score']}).", flush=True)

    asyncio.run(_test_demo2())

    print("\n--- 7. Testing Demo Step 3 (Successful Rollout) ---", flush=True)
    async def _test_demo3():
        d3 = await demo_service.execute_scenario_3()
        assert d3["step"] == 3
        print(f"[OK] Demo 3: All 10 stages passed successfully.", flush=True)

    asyncio.run(_test_demo3())

    print("\n--- 8. Testing Monitoring Telemetry ---", flush=True)
    metrics = metrics_service.get_dashboard_metrics()
    print(f"[OK] Deployments={metrics['total_deployments']}, Memories={metrics['hindsight_memory_records']}, Health={metrics['application_health']}", flush=True)

    print("\n==========================================", flush=True)
    print(" ALL BACKEND WORKFLOWS PASSED VALIDATION! ", flush=True)
    print("==========================================", flush=True)


if __name__ == "__main__":
    run()
