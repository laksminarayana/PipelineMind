import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel
from datetime import datetime, timezone

from backend.app.models.schemas import (
    Deployment, DeploymentCreate, PipelineRun, PipelineStage,
    Incident, IncidentCreate, IncidentResolveRequest,
    RiskAnalysisRequest, RiskAnalysisResponse,
    MemoryRetainRequest, MemoryRecallRequest, MemoryReflectRequest,
    AgentChatRequest, AgentChatResponse,
    RollbackRequest, RollbackResponse,
    Settings
)
from backend.app.services.deployment_service import deployment_service
from backend.app.services.pipeline_service import pipeline_service
from backend.app.services.incident_service import incident_service
from backend.app.services.metrics_service import metrics_service
from backend.app.services.demo_service import demo_service
from backend.app.analyzers.risk_analyzer import risk_analyzer
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.agent.devops_agent import devops_agent
from backend.app.database.connection import get_db

router = APIRouter()


# -------------------------------------------------------------
# Health Check
# -------------------------------------------------------------
@router.get("/health", tags=["Health"])
async def get_health():
    """
    Service health check endpoint.
    """
    memory_status = memory_manager.client.get_status()
    return {
        "status": "healthy",
        "service": "PipelineMind AI",
        "version": "1.0.0",
        "hindsight_memory": memory_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# -------------------------------------------------------------
# Deployments Endpoints
# -------------------------------------------------------------
@router.post("/deployments", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, tags=["Deployments"])
async def create_deployment(payload: DeploymentCreate):
    """
    Record a new deployment request.
    """
    try:
        dep = deployment_service.create_deployment(
            service_name=payload.service_name,
            environment=payload.environment,
            branch=payload.branch,
            commit_sha=payload.commit_sha,
            commit_message=payload.commit_message,
            author=payload.author,
            strategy=payload.strategy,
            config_diff=payload.config_diff
        )
        return dep
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create deployment: {str(e)}")


@router.get("/deployments", response_model=List[Dict[str, Any]], tags=["Deployments"])
async def list_deployments(limit: int = Query(50, ge=1, le=100)):
    """
    Retrieve recent deployment records.
    """
    return deployment_service.list_deployments(limit=limit)


@router.get("/deployments/{deployment_id}", response_model=Dict[str, Any], tags=["Deployments"])
async def get_deployment(deployment_id: str):
    """
    Get detailed deployment metadata by ID.
    """
    dep = deployment_service.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return dep


# -------------------------------------------------------------
# CI/CD Pipeline Endpoints
# -------------------------------------------------------------
class PipelineRunRequest(BaseModel):
    deployment_id: Optional[str] = None
    trigger_type: str = "manual"
    fail_at_stage: Optional[str] = None
    failure_error: Optional[str] = None
    strategy: str = "rolling"


@router.post("/pipeline/run", tags=["Pipeline"])
async def run_pipeline(payload: PipelineRunRequest):
    """
    Trigger simulated CI/CD pipeline execution across all 10 stages.
    """
    try:
        # Create or pick deployment
        dep_id = payload.deployment_id
        if not dep_id:
            dep = deployment_service.create_deployment(
                strategy=payload.strategy,
                commit_message=f"Pipeline run triggered ({payload.trigger_type})"
            )
            dep_id = dep["id"]

        run_init = pipeline_service.create_run(
            deployment_id=dep_id,
            trigger_type=payload.trigger_type,
            fail_at_stage=payload.fail_at_stage,
            failure_error=payload.failure_error
        )

        # Run pipeline execution task
        run_result = await pipeline_service.execute_pipeline(
            run_id=run_init["run_id"],
            deployment_id=dep_id,
            fail_at_stage=payload.fail_at_stage,
            failure_error=payload.failure_error,
            strategy=payload.strategy
        )

        # If failed, automatically record incident in Hindsight
        if run_result.get("status") == "failed":
            await incident_service.create_incident(
                deployment_id=dep_id,
                pipeline_stage=run_result.get("failed_stage", "health_verification"),
                error_message=run_result.get("error_message", "Stage failure detected"),
                infrastructure_changes="Triggered pipeline run configuration diff"
            )

        return run_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")


@router.get("/pipeline/status", tags=["Pipeline"])
async def get_pipeline_status(run_id: Optional[str] = None):
    """
    Get status and stage logs for a pipeline run (or latest run if unprovided).
    """
    if run_id:
        status_data = pipeline_service.get_run_status(run_id)
    else:
        status_data = pipeline_service.get_latest_run()

    if not status_data:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    return status_data


# -------------------------------------------------------------
# AI Risk Analysis Endpoints
# -------------------------------------------------------------
@router.post("/analyze", response_model=Dict[str, Any], tags=["Risk Analyzer"])
async def analyze_deployment_risk(payload: RiskAnalysisRequest):
    """
    Analyze Dockerfile, Kubernetes, DB configs, and dependencies using transparent heuristics,
    Hindsight historical memories, and Groq LLM explanations.
    """
    try:
        result = await risk_analyzer.analyze(
            dockerfile_diff=payload.dockerfile_diff or "",
            k8s_diff=payload.k8s_diff or "",
            dependency_diff=payload.dependency_diff or "",
            db_config_diff=payload.db_config_diff or "",
            strategy=payload.deployment_strategy or "rolling",
            commit_sha=payload.commit_sha or "HEAD"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Risk analysis error: {str(e)}")


# -------------------------------------------------------------
# Incidents Management Endpoints
# -------------------------------------------------------------
@router.post("/incidents", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, tags=["Incidents"])
async def create_incident(payload: IncidentCreate):
    """
    Record an incident and retain in Hindsight memory.
    """
    try:
        res = await incident_service.create_incident(
            deployment_id=payload.deployment_id,
            pipeline_stage=payload.pipeline_stage,
            error_message=payload.error_message,
            root_cause=payload.root_cause,
            infrastructure_changes=payload.infrastructure_changes,
            corrective_action=payload.corrective_action,
            fix_succeeded=payload.fix_succeeded
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record incident: {str(e)}")


@router.get("/incidents", response_model=List[Dict[str, Any]], tags=["Incidents"])
async def list_incidents(
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None)
):
    """
    List recorded incidents with search and filter support.
    """
    return incident_service.list_incidents(limit=limit, search=search)


@router.post("/incidents/{incident_id}/resolve", tags=["Incidents"])
async def resolve_incident(incident_id: str, payload: IncidentResolveRequest):
    """
    Mark an incident resolved with verified corrective action and update Hindsight memory bank.
    """
    updated = incident_service.resolve_incident(
        incident_id=incident_id,
        corrective_action=payload.corrective_action,
        fix_succeeded=payload.fix_succeeded,
        resolution_notes=payload.resolution_notes
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Incident not found")
    return updated


# -------------------------------------------------------------
# Hindsight Memory Endpoints
# -------------------------------------------------------------
@router.get("/memory", tags=["Hindsight Memory"])
async def get_memories(limit: int = Query(50, ge=1, le=100)):
    """
    List persistent memories from Hindsight memory bank with stats.
    """
    memories = memory_manager.get_all_memories(limit=limit)
    stats = memory_manager.get_memory_stats()
    return {
        "stats": stats,
        "memories": memories
    }


@router.post("/memory/retain", tags=["Hindsight Memory"])
async def retain_memory(payload: MemoryRetainRequest):
    """
    Directly retain content into Hindsight memory bank.
    """
    try:
        res = memory_manager.client.retain(
            content=payload.content,
            bank_id=payload.bank_id,
            metadata=payload.metadata
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory retention failed: {str(e)}")


@router.post("/memory/recall", tags=["Hindsight Memory"])
async def recall_memories(payload: MemoryRecallRequest):
    """
    Recall memories matching a query from Hindsight memory bank.
    """
    try:
        memories = memory_manager.recall_similar_incidents(
            query=payload.query,
            limit=payload.limit,
            bank_id=payload.bank_id
        )
        return {
            "query": payload.query,
            "bank_id": payload.bank_id,
            "results_count": len(memories),
            "memories": memories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory recall failed: {str(e)}")


@router.post("/memory/reflect", tags=["Hindsight Memory"])
async def reflect_memory(payload: MemoryReflectRequest):
    """
    Synthesize high-level observations and preventive learnings over memories.
    """
    try:
        reflection = memory_manager.reflect_on_incident(
            query=payload.query,
            bank_id=payload.bank_id,
            focus=payload.focus
        )
        return reflection
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory reflect failed: {str(e)}")


# -------------------------------------------------------------
# AI DevOps Assistant Chat
# -------------------------------------------------------------
@router.post("/agent/chat", response_model=Dict[str, Any], tags=["AI Assistant"])
async def agent_chat(payload: AgentChatRequest):
    """
    Ask the DevOps AI Assistant questions with Hindsight memory grounding.
    """
    try:
        response = await devops_agent.chat(
            user_message=payload.message,
            conversation_id=payload.conversation_id or "default-session",
            context=payload.context
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent chat error: {str(e)}")


# -------------------------------------------------------------
# Rollback Endpoint
# -------------------------------------------------------------
@router.post("/rollback", tags=["Deployments"])
async def rollback_deployment(payload: RollbackRequest):
    """
    Safely trigger automated rollback for a deployment.
    """
    try:
        result = deployment_service.rollback(
            deployment_id=payload.deployment_id,
            reason=payload.reason
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")


# -------------------------------------------------------------
# Monitoring & Metrics Endpoints
# -------------------------------------------------------------
@router.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    Get dashboard telemetry: CPU, memory, error rate, pod status.
    """
    return metrics_service.get_dashboard_metrics()


@router.get("/prometheus", tags=["Monitoring"])
async def get_prometheus_metrics():
    """
    Expose Prometheus text exposition format metrics.
    """
    raw_payload = metrics_service.get_prometheus_payload()
    return Response(content=raw_payload, media_type="text/plain; version=0.0.4; charset=utf-8")


# -------------------------------------------------------------
# Demonstration Scenario Endpoints (Section 5)
# -------------------------------------------------------------
class DemoStepRequest(BaseModel):
    step: int  # 1, 2, or 3


@router.post("/demo/run-step", tags=["Demonstration"])
async def run_demo_step(payload: DemoStepRequest):
    """
    Execute step 1, 2, or 3 of the Before-and-After Memory Learning demonstration.
    """
    if payload.step == 1:
        return await demo_service.execute_scenario_1()
    elif payload.step == 2:
        return await demo_service.execute_scenario_2()
    elif payload.step == 3:
        return await demo_service.execute_scenario_3()
    else:
        raise HTTPException(status_code=400, detail="Invalid demo step. Must be 1, 2, or 3.")


@router.post("/demo/reset", tags=["Demonstration"])
async def reset_demo_data():
    """
    Reset deployment and incident demo data to baseline state.
    """
    with get_db() as conn:
        conn.execute("DELETE FROM pipeline_stages;")
        conn.execute("DELETE FROM pipeline_runs;")
        conn.execute("DELETE FROM incidents;")
        conn.execute("DELETE FROM hindsight_memories WHERE incident_id IS NOT NULL;")
        conn.execute("DELETE FROM deployments WHERE id != 'dep-init-001';")

    return {"status": "success", "message": "Demo data reset to baseline."}


# -------------------------------------------------------------
# System Settings Endpoints
# -------------------------------------------------------------
@router.get("/settings", tags=["Settings"])
async def get_settings():
    with get_db() as conn:
        cursor = conn.execute("SELECT key, value FROM system_settings")
        settings_dict = {r["key"]: r["value"] for r in cursor.fetchall()}

    return {
        "groq_api_key": settings_dict.get("groq_api_key", ""),
        "groq_model": settings_dict.get("groq_model", "openai/gpt-oss-120b"),
        "hindsight_api_url": settings_dict.get("hindsight_api_url", "http://localhost:8888"),
        "hindsight_api_key": settings_dict.get("hindsight_api_key", ""),
        "hindsight_bank_id": settings_dict.get("hindsight_bank_id", "pipelinemind-devops"),
        "simulation_mode": settings_dict.get("simulation_mode", "true") == "true",
        "hindsight_status": memory_manager.client.get_status()
    }


@router.post("/settings", tags=["Settings"])
async def update_settings(payload: Settings):
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("groq_api_key", payload.groq_api_key or "", now)
        )
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("groq_model", payload.groq_model or "openai/gpt-oss-120b", now)
        )
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("hindsight_api_url", payload.hindsight_api_url or "http://localhost:8888", now)
        )
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("hindsight_api_key", payload.hindsight_api_key or "", now)
        )
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("hindsight_bank_id", payload.hindsight_bank_id or "pipelinemind-devops", now)
        )
        conn.execute(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("simulation_mode", "true" if payload.simulation_mode else "false", now)
        )

    # Re-initialize clients with updated configurations
    memory_manager.client.api_url = payload.hindsight_api_url
    memory_manager.client.api_key = payload.hindsight_api_key
    memory_manager.client.default_bank_id = payload.hindsight_bank_id
    memory_manager.client._initialize_client()

    return {"status": "success", "message": "Settings updated successfully"}
