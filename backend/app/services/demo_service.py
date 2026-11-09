import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.app.services.deployment_service import deployment_service
from backend.app.services.pipeline_service import pipeline_service
from backend.app.services.incident_service import incident_service
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.analyzers.risk_analyzer import risk_analyzer
from backend.app.agent.devops_agent import devops_agent
from backend.app.database.connection import get_db


class DemoService:
    """
    Executes the 3-step Before-and-After Memory Learning Demonstration Scenario.
    """

    def __init__(self):
        self.deployment = deployment_service
        self.pipeline = pipeline_service
        self.incident = incident_service
        self.memory = memory_manager
        self.risk = risk_analyzer
        self.agent = devops_agent

    async def execute_scenario_1(self) -> Dict[str, Any]:
        """
        DEPLOYMENT 1:
        1. Introduce database connection configuration failure.
        2. Pipeline detects failure at Stage 10 (Health verification).
        3. AI analyzes error & identifies root cause.
        4. Developer fixes configuration.
        5. Hindsight stores incident and successful resolution.
        """
        now = datetime.now(timezone.utc).isoformat()
        db_diff = (
            "--- a/config/database.env\n"
            "+++ b/config/database.env\n"
            "-DB_HOST=localhost:5432\n"
            "+DB_HOST=postgres-cluster.internal:5432\n"
            "+DB_TIMEOUT=5000\n"
            "+# WARNING: Missing DB_PASSWORD Kubernetes secret binding"
        )

        # 1. Create Deployment 1
        dep = self.deployment.create_deployment(
            service_name="order-processing-service",
            environment="production",
            branch="feature/db-migration",
            commit_sha="b24a91c",
            commit_message="Migrate database endpoint to postgres-cluster.internal",
            author="Alex Rivera <arivera@company.io>",
            strategy="rolling",
            config_diff=db_diff,
            risk_score=68,
            risk_level="Medium"
        )
        dep_id = dep["id"]

        # 2. Run Pipeline (Configured to fail at health_verification)
        run = self.pipeline.create_run(
            deployment_id=dep_id,
            trigger_type="demo",
            fail_at_stage="health_verification",
            failure_error="Fatal: Connection refused at postgres-cluster.internal:5432 after 30000ms. Pod enters CrashLoopBackOff."
        )
        run_res = await self.pipeline.execute_pipeline(
            run_id=run["run_id"],
            deployment_id=dep_id,
            config_diff=db_diff,
            fail_at_stage="health_verification",
            failure_error="Fatal: Connection refused at postgres-cluster.internal:5432 after 30000ms. Pod enters CrashLoopBackOff."
        )

        # 3. AI analyzes error & identifies root cause
        analysis = await self.agent.analyze_incident(
            deployment_id=dep_id,
            stage="health_verification",
            error_message="Connection refused at postgres-cluster.internal:5432 after 30000ms. Pod enters CrashLoopBackOff.",
            config_changes=db_diff
        )

        # 4 & 5. Create incident, apply developer fix, and retain in Hindsight
        root_cause = (
            "Database connection timeout caused by unreachable hostname 'postgres-cluster.internal:5432' "
            "and missing Kubernetes SecretKeyRef for database authentication credentials."
        )
        fix_action = (
            "Attached Kubernetes secret 'db-secret' with DB_PASSWORD and corrected CoreDNS hostname to "
            "'postgres-cluster.default.svc.cluster.local' with 20s initialDelay probe."
        )

        incident_res = await self.incident.create_incident(
            deployment_id=dep_id,
            pipeline_stage="health_verification",
            error_message="Connection refused at postgres-cluster.internal:5432 after 30000ms. Pod enters CrashLoopBackOff.",
            root_cause=root_cause,
            infrastructure_changes=db_diff,
            corrective_action=fix_action,
            fix_succeeded=True
        )

        # Update deployment record with applied fix
        with get_db() as conn:
            conn.execute("""
                UPDATE deployments
                SET applied_fix = ?
                WHERE id = ?
            """, (fix_action, dep_id))

        return {
            "step": 1,
            "title": "Deployment 1: Failure Detection, Root Cause & Memory Retention",
            "deployment": self.deployment.get_deployment(dep_id),
            "pipeline_run": self.pipeline.get_run_status(run["run_id"]),
            "ai_analysis": analysis,
            "incident": incident_res,
            "hindsight_learned": True,
            "memory_retained_summary": (
                f"Hindsight retained incident {incident_res['incident_id']} with verified remediation: '{fix_action}'."
            )
        }

    async def execute_scenario_2(self) -> Dict[str, Any]:
        """
        DEPLOYMENT 2:
        1. Introduce similar database configuration change.
        2. Agent retrieves previous incident from Hindsight.
        3. Agent recognizes similarity.
        4. Agent recommends previous successful fix.
        5. Displays deployment risk warning.
        """
        now = datetime.now(timezone.utc).isoformat()
        similar_db_diff = (
            "--- a/helm/values-prod.yaml\n"
            "+++ b/helm/values-prod.yaml\n"
            "-database_host: postgres-cluster.default.svc.cluster.local\n"
            "+database_host: internal-analytics-db.mesh.local\n"
            "+database_timeout_seconds: 10\n"
            "+# Note: Switching database endpoint without verifying secret bindings"
        )

        # 1. Create Deployment 2
        dep = self.deployment.create_deployment(
            service_name="order-processing-service",
            environment="production",
            branch="feature/analytics-db-switch",
            commit_sha="c89d12f",
            commit_message="Switch to internal-analytics-db mesh endpoint",
            author="DevOps Team <devops@company.io>",
            strategy="canary",
            config_diff=similar_db_diff,
            risk_score=84,
            risk_level="High"
        )
        dep_id = dep["id"]

        # 2. Risk Analyzer retrieves past incident from Hindsight
        risk_analysis = await self.risk.analyze(
            db_config_diff=similar_db_diff,
            strategy="canary",
            commit_sha="c89d12f"
        )

        # 3. Memory Recall & Reflection
        recalled = self.memory.recall_similar_incidents(
            query="database connection timeout postgres-cluster endpoint change",
            limit=3
        )
        reflection = self.memory.reflect_on_incident(
            query="database connection timeout endpoint change"
        )

        related_incidents = risk_analysis["related_incidents"]
        best_match = max(
            related_incidents,
            key=lambda memory: memory.get("similarity_score", 0.0),
            default=None,
        )
        if best_match:
            metadata = best_match.get("metadata", {})
            incident_id = metadata.get("incident_id") or best_match.get("id", "historical memory")
            similarity = round(best_match.get("similarity_score", 0.0) * 100)
            root_cause = metadata.get("root_cause") or best_match.get("content", "No root cause was retained.")
            corrective_action = metadata.get("corrective_action") or (
                "Review the recalled incident and validate the database credentials and endpoint."
            )
            agent_recommendation = (
                f"DEPLOYMENT RISK WARNING (Risk Score: {risk_analysis['risk_score']}/100 - "
                f"{risk_analysis['risk_category']} Risk):\n\n"
                f"Hindsight recalled incident {incident_id} with a {similarity}% similarity score.\n"
                f"Historical root cause: {root_cause}\n"
                f"Previously recorded corrective action: {corrective_action}"
            )
        else:
            agent_recommendation = (
                f"DEPLOYMENT RISK WARNING (Risk Score: {risk_analysis['risk_score']}/100 - "
                f"{risk_analysis['risk_category']} Risk):\n\n"
                "Hindsight did not return a related incident for this change. Follow the analyzer's "
                "preventive actions and verify credentials and endpoint connectivity before rollout."
            )

        return {
            "step": 2,
            "title": "Deployment 2: Hindsight Memory Recall & Proactive Risk Warning",
            "deployment": self.deployment.get_deployment(dep_id),
            "risk_analysis": risk_analysis,
            "recalled_memories": recalled,
            "reflection": reflection,
            "agent_recommendation": agent_recommendation,
            "similarity_detected": best_match is not None
        }

    async def execute_scenario_3(self) -> Dict[str, Any]:
        """
        DEPLOYMENT 3:
        1. Apply corrected configuration.
        2. Run pipeline again.
        3. Show successful deployment.
        4. Store successful deployment outcome.
        5. Show how agent's knowledge has improved.
        """
        now = datetime.now(timezone.utc).isoformat()
        corrected_diff = (
            "--- a/helm/values-prod.yaml\n"
            "+++ b/helm/values-prod.yaml\n"
            "+database_host: postgres-cluster.default.svc.cluster.local\n"
            "+secret_ref: db-secret\n"
            "+initial_delay_seconds: 20\n"
            "+liveness_probe: /healthz\n"
            "+# Verified against Hindsight Incident remediation standard"
        )

        # 1. Create Deployment 3
        dep = self.deployment.create_deployment(
            service_name="order-processing-service",
            environment="production",
            branch="main",
            commit_sha="d44e55a",
            commit_message="Apply verified DB config with secretKeyRef and 20s health probe",
            author="DevOps Engineer <devops@company.io>",
            strategy="canary",
            config_diff=corrected_diff,
            risk_score=14,
            risk_level="Low"
        )
        dep_id = dep["id"]

        # 2. Run Pipeline (Passes completely)
        run = self.pipeline.create_run(deployment_id=dep_id, trigger_type="demo")
        run_res = await self.pipeline.execute_pipeline(
            run_id=run["run_id"],
            deployment_id=dep_id,
            config_diff=corrected_diff,
            strategy="canary"
        )

        # 3. Retain successful deployment outcome in Hindsight
        retention = self.memory.retain_incident({
            "incident_id": "DEP-SUCCESS-003",
            "deployment_id": dep_id,
            "pipeline_stage": "health_verification",
            "error_message": "None",
            "root_cause": "N/A - Success",
            "infrastructure_changes": corrected_diff,
            "corrective_action": "Applied verified Hindsight remediation rules",
            "fix_succeeded": True,
            "timestamp": now,
            "memory_bank_id": "pipelinemind-devops"
        })

        recalled = self.memory.recall_similar_incidents(
            query="database connection timeout postgres endpoint secret",
            limit=3,
        )
        best_match = max(
            recalled,
            key=lambda memory: memory.get("similarity_score", 0.0),
            default=None,
        )
        learning_improvement = {
            "before_hindsight": {
                "deployment_1_outcome": "Pipeline Failed (30s DB Timeout)",
                "incident_diagnosis_time": "Manual triage required",
                "risk_warning": "None (Heuristics only)"
            },
            "after_hindsight": {
                "deployment_2_warning": (
                    f"Recalled historical memory with {round(best_match.get('similarity_score', 0.0) * 100)}% "
                    "similarity before deployment"
                    if best_match
                    else "No related historical memory was recalled"
                ),
                "deployment_3_outcome": (
                    "Pipeline succeeded"
                    if run_res.get("status") == "success"
                    else f"Pipeline {run_res.get('status', 'did not complete')}"
                ),
                "verified_fix_available": bool(
                    best_match
                    and best_match.get("metadata", {}).get("corrective_action")
                    and best_match.get("metadata", {}).get("fix_succeeded")
                ),
            }
        }

        return {
            "step": 3,
            "title": "Deployment 3: Successful Rollout & Demonstrated Knowledge Evolution",
            "deployment": self.deployment.get_deployment(dep_id),
            "pipeline_run": self.pipeline.get_run_status(run["run_id"]),
            "hindsight_retention": retention,
            "learning_improvement": learning_improvement
        }


demo_service = DemoService()
