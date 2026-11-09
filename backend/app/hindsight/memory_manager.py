import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.hindsight.client_wrapper import HindsightClientWrapper
from backend.app.database.connection import get_db

# Singleton client wrapper instance
_hindsight_wrapper = HindsightClientWrapper()


def get_hindsight_client() -> HindsightClientWrapper:
    return _hindsight_wrapper


class MemoryManager:
    """
    High-level DevOps Memory Manager wrapping Hindsight operations.
    Handles incident retention, contextual memory recall, and pattern reflection.
    """

    def __init__(self):
        self.client = get_hindsight_client()

    def retain_incident(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retain an incident in Hindsight with all required fields:
        - Incident ID
        - Deployment ID
        - Pipeline stage
        - Error message
        - Root cause
        - Infrastructure changes
        - Corrective action
        - Whether the fix succeeded
        - Timestamp
        """
        incident_id = incident.get("incident_id")
        deployment_id = incident.get("deployment_id")
        stage = incident.get("pipeline_stage")
        error = incident.get("error_message")
        root_cause = incident.get("root_cause")
        infra_changes = incident.get("infrastructure_changes")
        fix = incident.get("corrective_action")
        fix_succeeded = incident.get("fix_succeeded", False)
        timestamp = incident.get("timestamp") or datetime.now(timezone.utc).isoformat()
        bank_id = incident.get("memory_bank_id") or self.client.default_bank_id

        # Format descriptive text for Hindsight memory indexing
        content = (
            f"Deployment Incident [{incident_id}] during stage '{stage}' for deployment {deployment_id}. "
            f"Error: {error}. "
            f"Infrastructure changes: {infra_changes}. "
            f"Identified Root Cause: {root_cause}. "
            f"Corrective Action applied: {fix}. "
            f"Fix outcome: {'RESOLVED_SUCCESSFULLY' if fix_succeeded else 'UNRESOLVED_PENDING_VERIFICATION'}. "
            f"Timestamp: {timestamp}."
        )

        metadata = {
            "incident_id": incident_id,
            "deployment_id": deployment_id,
            "pipeline_stage": stage,
            "error_message": error,
            "root_cause": root_cause,
            "infrastructure_changes": infra_changes,
            "corrective_action": fix,
            "fix_succeeded": fix_succeeded,
            "timestamp": timestamp,
        }

        result = self.client.retain(content=content, bank_id=bank_id, metadata=metadata)
        return result

    def recall_similar_incidents(self, query: str, limit: int = 5, bank_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query Hindsight memory to retrieve past incidents matching current error or config change.
        """
        return self.client.recall(query=query, bank_id=bank_id, limit=limit)

    def reflect_on_incident(self, query: str, bank_id: Optional[str] = None, focus: Optional[str] = None) -> Dict[str, Any]:
        """
        Run Hindsight reflect to synthesize learned lessons and prevention recommendations.
        """
        return self.client.reflect(query=query, bank_id=bank_id, focus=focus)

    def get_all_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, bank_id, incident_id, content, metadata_json, tags, created_at
                FROM hindsight_memories
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

        results = []
        for r in rows:
            meta = json.loads(r["metadata_json"] or "{}")
            results.append({
                "id": r["id"],
                "bank_id": r["bank_id"],
                "incident_id": r["incident_id"],
                "content": r["content"],
                "metadata": meta,
                "tags": r["tags"].split(",") if r["tags"] else [],
                "created_at": r["created_at"],
                "provider": self.client.get_status()["label"]
            })
        return results

    def get_memory_stats(self) -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM hindsight_memories")
            total = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM hindsight_memories WHERE incident_id IS NOT NULL")
            incident_memories = cursor.fetchone()[0]

        status = self.client.get_status()
        return {
            "total_memories": total,
            "incident_memories": incident_memories,
            "bank_id": self.client.default_bank_id,
            "status": status,
            "last_synced_at": datetime.now(timezone.utc).isoformat()
        }


memory_manager = MemoryManager()
