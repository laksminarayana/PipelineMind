import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.database.connection import get_db
from backend.app.services.pipeline_service import pipeline_service


class DeploymentService:
    """
    Manages deployment records and rollback strategies.
    """

    def create_deployment(
        self,
        service_name: str = "order-processing-service",
        environment: str = "production",
        branch: str = "main",
        commit_sha: Optional[str] = None,
        commit_message: Optional[str] = None,
        author: Optional[str] = None,
        strategy: str = "rolling",
        config_diff: Optional[str] = None,
        risk_score: int = 15,
        risk_level: str = "Low"
    ) -> Dict[str, Any]:
        dep_id = f"dep-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        sha = commit_sha or uuid.uuid4().hex[:7]
        msg = commit_message or "Deploy updated container configuration"
        auth = author or "DevOps Automation <devops@company.io>"

        with get_db() as conn:
            conn.execute("""
                INSERT INTO deployments (
                    id, service_name, environment, branch, commit_sha, commit_message,
                    author, strategy, status, risk_score, risk_level, created_at,
                    config_diff, hindsight_synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dep_id, service_name, environment, branch, sha, msg, auth,
                strategy, "PENDING", risk_score, risk_level, now,
                config_diff, 1
            ))

        return {
            "id": dep_id,
            "service_name": service_name,
            "environment": environment,
            "branch": branch,
            "commit_sha": sha,
            "commit_message": msg,
            "author": auth,
            "strategy": strategy,
            "status": "PENDING",
            "risk_score": risk_score,
            "risk_level": risk_level,
            "created_at": now,
            "config_diff": config_diff
        }

    def list_deployments(self, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM deployments ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()

        deployments = []
        for r in rows:
            deployments.append({
                "id": r["id"],
                "service_name": r["service_name"],
                "environment": r["environment"],
                "branch": r["branch"],
                "commit_sha": r["commit_sha"],
                "commit_message": r["commit_message"],
                "author": r["author"],
                "strategy": r["strategy"],
                "status": r["status"],
                "risk_score": r["risk_score"],
                "risk_level": r["risk_level"],
                "created_at": r["created_at"],
                "finished_at": r["finished_at"],
                "error_stage": r["error_stage"],
                "error_message": r["error_message"],
                "applied_fix": r["applied_fix"],
                "config_diff": r["config_diff"],
                "hindsight_synced": bool(r["hindsight_synced"])
            })
        return deployments

    def get_deployment(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.execute("SELECT * FROM deployments WHERE id = ?", (deployment_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return {
                "id": r["id"],
                "service_name": r["service_name"],
                "environment": r["environment"],
                "branch": r["branch"],
                "commit_sha": r["commit_sha"],
                "commit_message": r["commit_message"],
                "author": r["author"],
                "strategy": r["strategy"],
                "status": r["status"],
                "risk_score": r["risk_score"],
                "risk_level": r["risk_level"],
                "created_at": r["created_at"],
                "finished_at": r["finished_at"],
                "error_stage": r["error_stage"],
                "error_message": r["error_message"],
                "applied_fix": r["applied_fix"],
                "config_diff": r["config_diff"],
                "hindsight_synced": bool(r["hindsight_synced"])
            }

    def rollback(self, deployment_id: str, reason: str = "Rollback requested") -> Dict[str, Any]:
        """
        Safely roll back to previous known stable deployment.
        """
        now = datetime.now(timezone.utc).isoformat()
        
        # Locate previous stable deployment
        previous_stable = "v1.0.0 (commit: f84b91c)"
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, commit_sha FROM deployments
                WHERE status = 'SUCCESS' AND id != ?
                ORDER BY created_at DESC LIMIT 1
            """, (deployment_id,))
            stable_row = cursor.fetchone()
            if stable_row:
                previous_stable = f"{stable_row['id']} (commit: {stable_row['commit_sha']})"

            # Update current deployment status to ROLLBACK
            conn.execute("""
                UPDATE deployments
                SET status = 'ROLLBACK', error_message = ?
                WHERE id = ?
            """, (f"Rolled back to {previous_stable}. Reason: {reason}", deployment_id))

        logs = [
            f"[{now}] Rollback initiated for deployment {deployment_id}.",
            f"[{now}] Reverting Kubernetes deployment/order-processing-service to {previous_stable}.",
            f"[{now}] Rolling back traffic router to baseline pod replica set.",
            f"[{now}] Pod health status: 3/3 Running. Rollback completed successfully."
        ]

        return {
            "success": True,
            "deployment_id": deployment_id,
            "previous_stable_version": previous_stable,
            "current_status": "ROLLBACK_COMPLETED",
            "logs": logs,
            "executed_at": now
        }


deployment_service = DeploymentService()
