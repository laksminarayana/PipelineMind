import os
import json
import logging
import re
import math
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.database.connection import get_db

logger = logging.getLogger(__name__)

# Attempt import of official hindsight_client if installed
try:
    from hindsight_client import Hindsight as VectorizeHindsightClient
    HINDSIGHT_CLIENT_INSTALLED = True
except ImportError:
    VectorizeHindsightClient = None
    HINDSIGHT_CLIENT_INSTALLED = False


class LocalHindsightEngine:
    """
    Clearly labeled SQLite demo substitute with retain, recall, and reflect operations.
    It is not a connection to Hindsight Cloud or a semantic memory service.
    """

    def __init__(self, bank_id: str = "pipelinemind-devops"):
        self.bank_id = bank_id

    def retain(self, bank_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        memory_id = f"mem-{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        metadata_dict = metadata or {}
        incident_id = metadata_dict.get("incident_id")

        # Extract tags / entity tokens
        tokens = re.findall(r'\b[A-Za-z0-9_-]{3,}\b', content.lower())
        tags = ",".join(sorted(list(set(tokens[:20]))))

        with get_db() as conn:
            conn.execute("""
                INSERT INTO hindsight_memories (
                    id, bank_id, incident_id, content, metadata_json, tags, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id, bank_id, incident_id, content,
                json.dumps(metadata_dict), tags, now
            ))

        return {
            "status": "success",
            "memory_id": memory_id,
            "bank_id": bank_id,
            "provider": "Hindsight Local Demo Engine (SQLite)",
            "retained_at": now
        }

    def recall(self, bank_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        query_tokens = set(re.findall(r'\b[A-Za-z0-9_-]{3,}\b', query.lower()))
        
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, bank_id, incident_id, content, metadata_json, tags, created_at
                FROM hindsight_memories
                WHERE bank_id = ?
                ORDER BY created_at DESC
            """, (bank_id,))
            rows = cursor.fetchall()

        scored_memories = []
        for r in rows:
            content = r["content"]
            metadata = json.loads(r["metadata_json"] or "{}")
            content_tokens = set(re.findall(r'\b[A-Za-z0-9_-]{3,}\b', content.lower()))
            
            # Multi-strategy scoring: Jaccard token overlap + exact phrase matching + metadata matching
            overlap = query_tokens.intersection(content_tokens)
            base_score = len(overlap) / (math.sqrt(len(query_tokens) * max(1, len(content_tokens))) or 1.0)
            
            # Boost if query phrases appear in error or root cause
            boost = 0.0
            query_lower = query.lower()
            if any(term in content.lower() for term in ["database", "postgres", "timeout", "crashloop", "secret", "connection"]):
                if any(term in query_lower for term in ["database", "postgres", "timeout", "crashloop", "secret", "connection"]):
                    boost += 0.25
            
            if metadata.get("stage") and metadata.get("stage") in query_lower:
                boost += 0.2

            score = min(1.0, base_score + boost)
            if score > 0.05 or len(rows) <= 3:
                scored_memories.append({
                    "id": r["id"],
                    "bank_id": r["bank_id"],
                    "incident_id": r["incident_id"],
                    "content": content,
                    "metadata": metadata,
                    "similarity_score": round(score, 3),
                    "created_at": r["created_at"],
                    "provider": "Hindsight Local Demo Engine (SQLite)"
                })

        scored_memories.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored_memories[:limit]

    def reflect(self, bank_id: str, query: str, focus: Optional[str] = None) -> Dict[str, Any]:
        """
        Synthesize query-focused reasoned summary over memories.
        """
        recalled = self.recall(bank_id, query, limit=5)
        if not recalled:
            return {
                "bank_id": bank_id,
                "query": query,
                "synthesis": "No prior incidents or deployment records matched this scenario in Hindsight memory.",
                "confidence": 0.2,
                "incident_count": 0,
                "learned_patterns": [],
                "provider": "Hindsight Local Demo Engine (SQLite)"
            }

        patterns = []
        successful_fixes = []
        for mem in recalled:
            meta = mem.get("metadata", {})
            if meta.get("corrective_action") and meta.get("fix_succeeded"):
                successful_fixes.append(meta.get("corrective_action"))
            if meta.get("root_cause"):
                patterns.append(meta.get("root_cause"))

        synthesis_lines = [
            f"Synthesizing observations across {len(recalled)} relevant deployment incident(s) for query: '{query}'.",
        ]
        if patterns:
            synthesis_lines.append(f"Primary historical root causes detected: {'; '.join(set(patterns[:3]))}.")
        if successful_fixes:
            synthesis_lines.append(f"Historically verified remediation: {'; '.join(set(successful_fixes[:2]))}.")
        else:
            synthesis_lines.append("Recommend validating service secrets and container network health checks.")

        return {
            "bank_id": bank_id,
            "query": query,
            "synthesis": " ".join(synthesis_lines),
            "confidence": 0.88 if len(recalled) >= 1 else 0.5,
            "incident_count": len(recalled),
            "recalled_memories": recalled,
            "learned_patterns": list(set(patterns)),
            "provider": "Hindsight Local Demo Engine (SQLite)"
        }


class HindsightClientWrapper:
    """
    Unified Hindsight client supporting official Vectorize Hindsight SDK with
    automatic fallback to LocalHindsightEngine when credentials/endpoint are unset.
    """

    def __init__(self):
        self.api_url = os.getenv("HINDSIGHT_API_URL", "http://localhost:8888")
        self.api_key = os.getenv("HINDSIGHT_API_KEY", "")
        self.default_bank_id = os.getenv("HINDSIGHT_BANK_ID", "pipelinemind-devops")

        self.remote_client = None
        self.is_remote_connected = False
        self.remote_error = None
        self.local_engine = LocalHindsightEngine(bank_id=self.default_bank_id)

        self._initialize_client()

    def _initialize_client(self):
        if HINDSIGHT_CLIENT_INSTALLED and self.api_url and self.api_key:
            try:
                self.remote_client = VectorizeHindsightClient(
                    base_url=self.api_url,
                    api_key=self.api_key if self.api_key else None
                )
                self.is_remote_connected = False
                self.remote_error = None
            except Exception:
                self.remote_client = None
                self.is_remote_connected = False
                self.remote_error = "Hindsight client could not be initialized."
        else:
            self.remote_client = None
            self.is_remote_connected = False
            self.remote_error = None

    def get_status(self) -> Dict[str, Any]:
        if self.is_remote_connected:
            label = "Hindsight by Vectorize (connected)"
        elif self.remote_client:
            label = "Hindsight by Vectorize (configured; connection unverified)"
        else:
            label = "Hindsight Local Demo Bank (SQLite)"
        return {
            "sdk_installed": HINDSIGHT_CLIENT_INSTALLED,
            "is_connected_to_cloud": self.is_remote_connected,
            "is_configured": self.remote_client is not None,
            "mode": (
                "hindsight_cloud"
                if self.is_remote_connected
                else "hindsight_configured"
                if self.remote_client
                else "local_demo"
            ),
            "api_url": self.api_url,
            "default_bank_id": self.default_bank_id,
            "label": label,
            "last_remote_error": self.remote_error,
        }

    def retain(self, content: str, bank_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        target_bank = bank_id or self.default_bank_id
        
        # Always retain locally for redundancy and dashboard visualization
        local_res = self.local_engine.retain(bank_id=target_bank, content=content, metadata=metadata)

        if self.remote_client:
            try:
                remote_res = self.remote_client.retain(
                    bank_id=target_bank,
                    content=content,
                    metadata={
                        key: json.dumps(value, ensure_ascii=True, default=str)
                        for key, value in (metadata or {}).items()
                    },
                )
                self.is_remote_connected = bool(remote_res.success)
                self.remote_error = None if self.is_remote_connected else "Hindsight did not confirm memory retention."
                return {
                    **local_res,
                    "remote_synced": self.is_remote_connected,
                    "provider": (
                        "Hindsight by Vectorize (Official Server)"
                        if self.is_remote_connected
                        else local_res["provider"]
                    ),
                }
            except Exception:
                self.is_remote_connected = False
                self.remote_error = "Hindsight memory retention failed; retained locally instead."
                logger.warning(self.remote_error)
                return {
                    **local_res,
                    "remote_synced": False,
                    "remote_warning": self.remote_error,
                    "provider": "Hindsight Local Demo Engine (SQLite)",
                }

        return local_res

    def recall(self, query: str, bank_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        target_bank = bank_id or self.default_bank_id

        if self.remote_client:
            try:
                remote_response = self.remote_client.recall(bank_id=target_bank, query=query)
                self.is_remote_connected = True
                self.remote_error = None
                memories = []
                for item in remote_response.results[:limit]:
                    metadata = {
                        key: self._decode_metadata_value(value)
                        for key, value in (item.metadata or {}).items()
                    }
                    memories.append({
                        "id": item.id,
                        "bank_id": target_bank,
                        "content": item.text,
                        "metadata": metadata,
                        "similarity_score": (
                            min(1.0, max(0.0, item.scores.final))
                            if item.scores
                            else 0.0
                        ),
                        "created_at": item.mentioned_at or item.occurred_start,
                        "provider": "Hindsight by Vectorize (Official Server)",
                    })
                return memories
            except Exception:
                self.is_remote_connected = False
                self.remote_error = "Hindsight recall failed; using local demo memories."
                logger.warning(self.remote_error)

        return self.local_engine.recall(bank_id=target_bank, query=query, limit=limit)

    def reflect(self, query: str, bank_id: Optional[str] = None, focus: Optional[str] = None) -> Dict[str, Any]:
        target_bank = bank_id or self.default_bank_id

        if self.remote_client:
            try:
                remote_reflection = self.remote_client.reflect(
                    bank_id=target_bank,
                    query=query,
                    context=focus,
                )
                self.is_remote_connected = True
                self.remote_error = None
                if remote_reflection:
                    return {
                        "bank_id": target_bank,
                        "query": query,
                        "synthesis": remote_reflection.text,
                        "provider": "Hindsight by Vectorize (Official Server)",
                    }
            except Exception:
                self.is_remote_connected = False
                self.remote_error = "Hindsight reflection failed; using local demo memories."
                logger.warning(self.remote_error)

        return self.local_engine.reflect(bank_id=target_bank, query=query, focus=focus)

    @staticmethod
    def _decode_metadata_value(value: str) -> Any:
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return value
