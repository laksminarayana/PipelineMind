import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.database.connection import get_db
from backend.app.analyzers.risk_analyzer import risk_analyzer
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.services.metrics_service import (
    PROMETHEUS_DEPLOYMENTS_TOTAL,
    PROMETHEUS_PIPELINE_DURATION_SECONDS,
)

PIPELINE_STAGES = [
    {"order": 1, "id": "github_source", "name": "GitHub source"},
    {"order": 2, "id": "build", "name": "Build"},
    {"order": 3, "id": "unit_testing", "name": "Unit testing"},
    {"order": 4, "id": "code_quality", "name": "Code quality"},
    {"order": 5, "id": "security_scanning", "name": "Security scanning (Trivy)"},
    {"order": 6, "id": "docker_image", "name": "Docker image creation"},
    {"order": 7, "id": "ai_risk_analysis", "name": "AI risk analysis"},
    {"order": 8, "id": "deployment_approval", "name": "Deployment approval"},
    {"order": 9, "id": "k8s_deployment", "name": "Kubernetes deployment"},
    {"order": 10, "id": "health_verification", "name": "Health verification"},
]


class PipelineService:
    """
    Manages CI/CD pipeline runs across the 10 stages, emitting realistic logs
    and integrating with AI Risk Analysis and Hindsight Memory.
    """

    def __init__(self):
        self.risk = risk_analyzer
        self.memory = memory_manager

    def create_run(
        self,
        deployment_id: str,
        trigger_type: str = "manual",
        fail_at_stage: Optional[str] = None,
        failure_error: Optional[str] = None
    ) -> Dict[str, Any]:
        run_id = f"run-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        stages_data = []
        with get_db() as conn:
            # Create Pipeline Run record
            conn.execute("""
                INSERT INTO pipeline_runs (
                    run_id, deployment_id, status, trigger_type, current_stage_index,
                    overall_risk_score, overall_risk_level, logs, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, deployment_id, "running", trigger_type, 0,
                20, "Low", json.dumps([f"[{now}] Pipeline execution triggered ({trigger_type})"]),
                now, now
            ))

            for stg in PIPELINE_STAGES:
                stage_record_id = f"{run_id}-{stg['id']}"
                conn.execute("""
                    INSERT INTO pipeline_stages (
                        id, run_id, name, stage_order, status, duration_seconds, details, logs, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    stage_record_id, run_id, stg["name"], stg["order"], "pending",
                    0.0, "Queued in runner pool", json.dumps([]), now
                ))

                stages_data.append({
                    "id": stage_record_id,
                    "stage_key": stg["id"],
                    "name": stg["name"],
                    "order": stg["order"],
                    "status": "pending",
                    "duration_seconds": 0.0,
                    "details": "Queued in runner pool",
                    "logs": []
                })

        return {
            "run_id": run_id,
            "deployment_id": deployment_id,
            "status": "running",
            "stages": stages_data,
            "fail_at_stage": fail_at_stage,
            "failure_error": failure_error
        }

    async def execute_pipeline(
        self,
        run_id: str,
        deployment_id: str,
        config_diff: Optional[str] = None,
        fail_at_stage: Optional[str] = None,
        failure_error: Optional[str] = None,
        strategy: str = "rolling"
    ) -> Dict[str, Any]:
        """
        Execute stages sequentially with realistic timing, logs, and telemetry.
        """
        run_logs = []
        overall_status = "success"
        pipeline_duration = 0.0

        for stage_idx, stg in enumerate(PIPELINE_STAGES):
            stage_key = stg["id"]
            stage_name = stg["name"]
            stage_record_id = f"{run_id}-{stage_key}"
            start_time = datetime.now(timezone.utc).isoformat()

            # Mark running
            self._update_stage_status(stage_record_id, "running", "Executing task...", 0.5)

            # Stage execution simulation & log generation
            stage_logs = []
            duration = 1.0

            if stage_key == "github_source":
                stage_logs.append("Fetching commit sha HEAD from origin/main...")
                stage_logs.append("Git tree clean. 14 files modified, 3 submodules verified.")
                duration = 0.8
            elif stage_key == "build":
                stage_logs.append("Compiling application sources with Python 3.13...")
                stage_logs.append("Installing locked dependencies from pyproject.toml...")
                stage_logs.append("Bytecode compilation complete. 0 syntax errors.")
                duration = 1.2
            elif stage_key == "unit_testing":
                stage_logs.append("Running test suite with pytest...")
                stage_logs.append("tests/test_api.py::test_health PASSED [33%]")
                stage_logs.append("tests/test_service.py::test_orders PASSED [66%]")
                stage_logs.append("tests/test_memory.py::test_recall PASSED [100%]")
                stage_logs.append("3 passed in 0.42s")
                duration = 1.0
            elif stage_key == "code_quality":
                stage_logs.append("Running Ruff & Flake8 linter checks...")
                stage_logs.append("All checks passed! Code quality score: 9.8/10.")
                duration = 0.6
            elif stage_key == "security_scanning":
                stage_logs.append("Executing Trivy vulnerability scanner...")
                stage_logs.append("Target image: order-processing-service:latest")
                stage_logs.append("Vulnerabilities: 0 CRITICAL, 0 HIGH, 1 MEDIUM (CVE-2024-ignore).")
                stage_logs.append("Trivy policy check: PASSED.")
                duration = 1.1
            elif stage_key == "docker_image":
                stage_logs.append("Building container image: ghcr.io/company/order-processing-service:v2.1.0")
                stage_logs.append("Pushing layers to container registry (digest: sha256:7f9a8b1c)...")
                stage_logs.append("Image pushed successfully.")
                duration = 1.3
            elif stage_key == "ai_risk_analysis":
                stage_logs.append("Running PipelineMind AI Risk Analyzer...")
                risk_res = await self.risk.analyze(
                    db_config_diff=config_diff if "DB" in (config_diff or "") else "",
                    strategy=strategy
                )
                stage_logs.append(f"AI Risk Score: {risk_res['risk_score']}/100 ({risk_res['risk_category']})")
                stage_logs.append(f"Decision: {risk_res['deployment_decision']}")
                for r in risk_res["reasons"][:2]:
                    stage_logs.append(f"• Reason: {r}")
                duration = 1.0
            elif stage_key == "deployment_approval":
                stage_logs.append("Checking automated approval rules...")
                stage_logs.append("Deployment strategy: " + strategy.upper())
                stage_logs.append("Automated policy check: APPROVED for rollout.")
                duration = 0.5
            elif stage_key == "k8s_deployment":
                stage_logs.append(f"Applying Kubernetes Deployment manifest with strategy: {strategy}...")
                stage_logs.append("Updated deployment.apps/order-processing-service")
                stage_logs.append("Waiting for rollout to finish: 1 of 3 updated replicas are available...")
                duration = 1.5
            elif stage_key == "health_verification":
                stage_logs.append("Probing application endpoints: GET /healthz...")
                duration = 1.2

            pipeline_duration += duration

            # Check if this stage is instructed to fail
            if fail_at_stage and (fail_at_stage == stage_key or (fail_at_stage in stage_name.lower())):
                err_msg = failure_error or "Service health probe timed out after 30000ms: connection refused at postgres-cluster.internal:5432"
                stage_logs.append(f"CRITICAL ERROR: {err_msg}")
                self._update_stage_status(
                    stage_record_id, "failed", f"Failed: {err_msg}", duration,
                    error_message=err_msg, logs=stage_logs
                )
                overall_status = "failed"
                
                # Mark remaining stages skipped
                for rem in PIPELINE_STAGES[stage_idx + 1:]:
                    self._update_stage_status(
                        f"{run_id}-{rem['id']}", "skipped", "Skipped due to upstream stage failure", 0.0
                    )

                self._update_pipeline_run(run_id, "failed", stage_idx, logs=stage_logs)
                self._update_deployment_status(
                    deployment_id, "FAILED", error_stage=stage_name, error_message=err_msg
                )
                PROMETHEUS_DEPLOYMENTS_TOTAL.labels(
                    status="failed",
                    strategy=strategy if strategy in {"rolling", "blue-green", "canary"} else "other",
                ).inc()
                PROMETHEUS_PIPELINE_DURATION_SECONDS.observe(pipeline_duration)
                return {
                    "run_id": run_id,
                    "deployment_id": deployment_id,
                    "status": "failed",
                    "failed_stage": stage_name,
                    "error_message": err_msg
                }

            # If not failed, complete stage successfully
            self._update_stage_status(
                stage_record_id, "success", "Completed successfully", duration, logs=stage_logs
            )
            run_logs.extend(stage_logs)

        # All stages succeeded
        self._update_pipeline_run(run_id, "success", 10, logs=run_logs)
        self._update_deployment_status(deployment_id, "SUCCESS")
        PROMETHEUS_DEPLOYMENTS_TOTAL.labels(
            status="success",
            strategy=strategy if strategy in {"rolling", "blue-green", "canary"} else "other",
        ).inc()
        PROMETHEUS_PIPELINE_DURATION_SECONDS.observe(pipeline_duration)

        return {
            "run_id": run_id,
            "deployment_id": deployment_id,
            "status": "success",
            "completed_stages": 10
        }

    def _update_stage_status(
        self,
        stage_id: str,
        status: str,
        details: str,
        duration: float,
        error_message: Optional[str] = None,
        logs: Optional[List[str]] = None
    ):
        with get_db() as conn:
            conn.execute("""
                UPDATE pipeline_stages
                SET status = ?, details = ?, duration_seconds = ?, error_message = ?, logs = ?, timestamp = ?
                WHERE id = ?
            """, (
                status, details, duration, error_message,
                json.dumps(logs or []), datetime.now(timezone.utc).isoformat(), stage_id
            ))

    def _update_pipeline_run(self, run_id: str, status: str, current_index: int, logs: List[str]):
        with get_db() as conn:
            conn.execute("""
                UPDATE pipeline_runs
                SET status = ?, current_stage_index = ?, logs = ?, updated_at = ?
                WHERE run_id = ?
            """, (
                status, current_index, json.dumps(logs),
                datetime.now(timezone.utc).isoformat(), run_id
            ))

    def _update_deployment_status(
        self,
        deployment_id: str,
        status: str,
        error_stage: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        with get_db() as conn:
            conn.execute("""
                UPDATE deployments
                SET status = ?, finished_at = ?, error_stage = ?, error_message = ?
                WHERE id = ?
            """, (
                status, datetime.now(timezone.utc).isoformat(), error_stage, error_message, deployment_id
            ))

    def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,))
            run_row = cursor.fetchone()
            if not run_row:
                return None

            cursor = conn.execute("""
                SELECT * FROM pipeline_stages WHERE run_id = ? ORDER BY stage_order ASC
            """, (run_id,))
            stage_rows = cursor.fetchall()

        stages = []
        for s in stage_rows:
            stages.append({
                "id": s["id"],
                "name": s["name"],
                "order": s["stage_order"],
                "status": s["status"],
                "duration_seconds": s["duration_seconds"],
                "details": s["details"],
                "error_message": s["error_message"],
                "logs": json.loads(s["logs"] or "[]"),
                "timestamp": s["timestamp"]
            })

        return {
            "run_id": run_row["run_id"],
            "deployment_id": run_row["deployment_id"],
            "status": run_row["status"],
            "trigger_type": run_row["trigger_type"],
            "current_stage_index": run_row["current_stage_index"],
            "overall_risk_score": run_row["overall_risk_score"],
            "overall_risk_level": run_row["overall_risk_level"],
            "stages": stages,
            "created_at": run_row["created_at"],
            "updated_at": run_row["updated_at"]
        }

    def get_latest_run(self) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.execute("SELECT run_id FROM pipeline_runs ORDER BY created_at DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                return self.get_run_status(row["run_id"])
        return None


pipeline_service = PipelineService()
