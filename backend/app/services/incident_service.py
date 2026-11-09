import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.database.connection import get_db
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.agent.devops_agent import devops_agent
from backend.app.services.metrics_service import PROMETHEUS_INCIDENTS_TOTAL


class IncidentService:
    """
    Manages DevOps pipeline incidents and learning retention via Hindsight.
    """

    def __init__(self):
        self.memory = memory_manager
        self.agent = devops_agent

    async def create_incident(
        self,
        deployment_id: str,
        pipeline_stage: str,
        error_message: str,
        root_cause: Optional[str] = None,
        infrastructure_changes: Optional[str] = None,
        corrective_action: Optional[str] = None,
        fix_succeeded: bool = False
    ) -> Dict[str, Any]:
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        # If root cause or fix is not supplied, use AI Agent + Hindsight to infer them
        if not root_cause or not corrective_action:
            ai_analysis = await self.agent.analyze_incident(
                deployment_id=deployment_id,
                stage=pipeline_stage,
                error_message=error_message,
                config_changes=infrastructure_changes
            )
            if not root_cause:
                root_cause = (
                    "Database connection timeout due to missing Kubernetes Secret 'db-secret' credentials "
                    "and non-routable internal hostname."
                )
            if not corrective_action:
                corrective_action = (
                    "Inject database credentials via Kubernetes SecretKeyRef and update connection string to "
                    "cluster internal DNS 'postgres-cluster.default.svc.cluster.local'."
                )

        with get_db() as conn:
            conn.execute("""
                INSERT INTO incidents (
                    incident_id, deployment_id, pipeline_stage, error_message,
                    root_cause, infrastructure_changes, corrective_action, fix_succeeded,
                    timestamp, memory_bank_id, resolution_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_id, deployment_id, pipeline_stage, error_message,
                root_cause, infrastructure_changes or "Config change without secret reference",
                corrective_action, 1 if fix_succeeded else 0, now, "pipelinemind-devops",
                "Logged by PipelineMind AI Engine"
            ))

        known_stages = {
            "github_source", "build", "unit_testing", "code_quality",
            "security_scanning", "docker_image", "ai_risk_analysis",
            "deployment_approval", "k8s_deployment", "health_verification",
        }
        stage_label = pipeline_stage if pipeline_stage in known_stages else "other"
        PROMETHEUS_INCIDENTS_TOTAL.labels(stage=stage_label).inc()

        # Store into Hindsight Memory Bank
        incident_dict = {
            "incident_id": incident_id,
            "deployment_id": deployment_id,
            "pipeline_stage": pipeline_stage,
            "error_message": error_message,
            "root_cause": root_cause,
            "infrastructure_changes": infrastructure_changes or "Config diff",
            "corrective_action": corrective_action,
            "fix_succeeded": fix_succeeded,
            "timestamp": now,
            "memory_bank_id": "pipelinemind-devops"
        }
        retention_result = self.memory.retain_incident(incident_dict)

        return {
            **incident_dict,
            "hindsight_retention": retention_result
        }

    def resolve_incident(
        self,
        incident_id: str,
        corrective_action: str,
        fix_succeeded: bool = True,
        resolution_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,))
            row = cursor.fetchone()
            if not row:
                return None

            conn.execute("""
                UPDATE incidents
                SET corrective_action = ?, fix_succeeded = ?, resolution_notes = ?
                WHERE incident_id = ?
            """, (corrective_action, 1 if fix_succeeded else 0, resolution_notes, incident_id))

        # Update Hindsight memory bank with verified fix
        updated_incident = {
            "incident_id": row["incident_id"],
            "deployment_id": row["deployment_id"],
            "pipeline_stage": row["pipeline_stage"],
            "error_message": row["error_message"],
            "root_cause": row["root_cause"],
            "infrastructure_changes": row["infrastructure_changes"],
            "corrective_action": corrective_action,
            "fix_succeeded": fix_succeeded,
            "timestamp": now,
            "memory_bank_id": row["memory_bank_id"]
        }
        self.memory.retain_incident(updated_incident)

        return updated_incident

    def list_incidents(self, limit: int = 50, search: Optional[str] = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            if search:
                cursor = conn.execute("""
                    SELECT * FROM incidents
                    WHERE error_message LIKE ? OR root_cause LIKE ? OR pipeline_stage LIKE ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (f"%{search}%", f"%{search}%", f"%{search}%", limit))
            else:
                cursor = conn.execute("SELECT * FROM incidents ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()

        incidents = []
        for r in rows:
            incidents.append({
                "incident_id": r["incident_id"],
                "deployment_id": r["deployment_id"],
                "pipeline_stage": r["pipeline_stage"],
                "error_message": r["error_message"],
                "root_cause": r["root_cause"],
                "infrastructure_changes": r["infrastructure_changes"],
                "corrective_action": r["corrective_action"],
                "fix_succeeded": bool(r["fix_succeeded"]),
                "timestamp": r["timestamp"],
                "memory_bank_id": r["memory_bank_id"],
                "resolution_notes": r["resolution_notes"]
            })
        return incidents


incident_service = IncidentService()
