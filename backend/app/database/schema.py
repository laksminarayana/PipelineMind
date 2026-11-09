import json
import uuid
from datetime import datetime, timezone
from backend.app.database.connection import get_db


def init_db():
    with get_db() as conn:
        # Deployments table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS deployments (
            id TEXT PRIMARY KEY,
            service_name TEXT NOT NULL,
            environment TEXT NOT NULL,
            branch TEXT NOT NULL,
            commit_sha TEXT NOT NULL,
            commit_message TEXT NOT NULL,
            author TEXT NOT NULL,
            strategy TEXT NOT NULL,
            status TEXT NOT NULL,
            risk_score INTEGER DEFAULT 15,
            risk_level TEXT DEFAULT 'Low',
            created_at TEXT NOT NULL,
            finished_at TEXT,
            error_stage TEXT,
            error_message TEXT,
            applied_fix TEXT,
            config_diff TEXT,
            hindsight_synced INTEGER DEFAULT 0
        );
        """)

        # Pipeline Runs
        conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY,
            deployment_id TEXT NOT NULL,
            status TEXT NOT NULL,
            trigger_type TEXT DEFAULT 'manual',
            current_stage_index INTEGER DEFAULT 0,
            overall_risk_score INTEGER DEFAULT 0,
            overall_risk_level TEXT DEFAULT 'Low',
            logs TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (deployment_id) REFERENCES deployments (id)
        );
        """)

        # Pipeline Stages
        conn.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_stages (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            name TEXT NOT NULL,
            stage_order INTEGER NOT NULL,
            status TEXT NOT NULL,
            duration_seconds REAL DEFAULT 0.0,
            details TEXT DEFAULT '',
            error_message TEXT,
            logs TEXT DEFAULT '[]',
            timestamp TEXT,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id)
        );
        """)

        # Incidents
        conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id TEXT PRIMARY KEY,
            deployment_id TEXT NOT NULL,
            pipeline_stage TEXT NOT NULL,
            error_message TEXT NOT NULL,
            root_cause TEXT NOT NULL,
            infrastructure_changes TEXT NOT NULL,
            corrective_action TEXT NOT NULL,
            fix_succeeded INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            similarity_score REAL,
            memory_bank_id TEXT DEFAULT 'pipelinemind-devops',
            resolution_notes TEXT,
            FOREIGN KEY (deployment_id) REFERENCES deployments (id)
        );
        """)

        # Hindsight Memories (Local persistent memory bank store)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS hindsight_memories (
            id TEXT PRIMARY KEY,
            bank_id TEXT NOT NULL,
            incident_id TEXT,
            content TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            tags TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );
        """)

        # System Settings
        conn.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)

        # Seed initial settings if absent
        cursor = conn.execute("SELECT COUNT(*) FROM system_settings WHERE key = 'groq_model'")
        if cursor.fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("groq_model", "openai/gpt-oss-120b", now)
            )
            conn.execute(
                "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("hindsight_bank_id", "pipelinemind-devops", now)
            )
            conn.execute(
                "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("simulation_mode", "true", now)
            )
            conn.execute(
                "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("hindsight_api_url", "http://localhost:8888", now)
            )


def seed_initial_data_if_empty():
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM deployments")
        count = cursor.fetchone()[0]
        if count > 0:
            return

        now = datetime.now(timezone.utc).isoformat()
        
        # Historical Deployment 0: Baseline successful deployment
        dep_id = "dep-init-001"
        conn.execute("""
            INSERT INTO deployments (
                id, service_name, environment, branch, commit_sha, commit_message,
                author, strategy, status, risk_score, risk_level, created_at, finished_at,
                hindsight_synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dep_id, "order-processing-service", "production", "main", "f84b91c",
            "Initial microservice deployment v1.0.0 with Redis cache",
            "Sarah Jenkins <sjenkins@company.io>", "rolling", "SUCCESS",
            12, "Low", now, now, 1
        ))

        # Memory entry for baseline
        mem_id = f"mem-{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO hindsight_memories (
                id, bank_id, incident_id, content, metadata_json, tags, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            mem_id, "pipelinemind-devops", None,
            "Baseline deployment v1.0.0 for order-processing-service succeeded with PostgreSQL connection pool max=20, timeout=10s, and healthy liveness probe on /healthz.",
            json.dumps({"stage": "health_verification", "status": "success", "service": "order-processing-service"}),
            "baseline,postgres,healthz,rolling", now
        ))
