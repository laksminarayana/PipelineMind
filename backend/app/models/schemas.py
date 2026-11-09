from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class DeploymentBase(BaseModel):
    service_name: str = "order-processing-service"
    environment: str = "production"
    branch: str = "main"
    commit_sha: str = "a1b2c3d"
    commit_message: str = "Update service configuration and dependencies"
    author: str = "DevOps Engineer <devops@company.io>"
    strategy: str = "rolling"  # rolling, blue-green, canary
    config_diff: Optional[str] = None


class DeploymentCreate(DeploymentBase):
    pass


class Deployment(DeploymentBase):
    id: str
    status: str  # PENDING, RUNNING, SUCCESS, FAILED, ROLLBACK
    risk_score: int = 15
    risk_level: str = "Low"  # Low, Medium, High
    created_at: str
    finished_at: Optional[str] = None
    error_stage: Optional[str] = None
    error_message: Optional[str] = None
    applied_fix: Optional[str] = None
    hindsight_synced: bool = False


class PipelineStage(BaseModel):
    id: str
    name: str
    order: int
    status: str = "pending"  # pending, running, success, failed, skipped
    duration_seconds: float = 0.0
    details: str = "Awaiting execution"
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    timestamp: Optional[str] = None


class PipelineRun(BaseModel):
    run_id: str
    deployment_id: str
    status: str = "pending"  # pending, running, success, failed, aborted
    trigger_type: str = "manual"  # manual, webhook, demo
    current_stage_index: int = 0
    stages: List[PipelineStage] = Field(default_factory=list)
    overall_risk_score: int = 0
    overall_risk_level: str = "Low"
    logs: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str


class Incident(BaseModel):
    incident_id: str
    deployment_id: str
    pipeline_stage: str
    error_message: str
    root_cause: str
    infrastructure_changes: str
    corrective_action: str
    fix_succeeded: bool = False
    timestamp: str
    similarity_score: Optional[float] = None
    memory_bank_id: str = "pipelinemind-devops"
    resolution_notes: Optional[str] = None


class IncidentCreate(BaseModel):
    deployment_id: str
    pipeline_stage: str
    error_message: str
    root_cause: str
    infrastructure_changes: str
    corrective_action: str
    fix_succeeded: bool = False
    memory_bank_id: str = "pipelinemind-devops"


class IncidentResolveRequest(BaseModel):
    corrective_action: str
    fix_succeeded: bool = True
    resolution_notes: Optional[str] = None


class RiskAnalysisRequest(BaseModel):
    commit_sha: Optional[str] = "HEAD"
    branch: Optional[str] = "main"
    dockerfile_diff: Optional[str] = ""
    k8s_diff: Optional[str] = ""
    dependency_diff: Optional[str] = ""
    db_config_diff: Optional[str] = ""
    deployment_strategy: Optional[str] = "rolling"


class RiskAnalysisResponse(BaseModel):
    risk_score: int  # 0 to 100
    risk_category: str  # Low, Medium, High
    reasons: List[str]
    related_incidents: List[Incident] = Field(default_factory=list)
    recommended_preventive_actions: List[str]
    deployment_decision: str  # APPROVED, REVIEW_REQUIRED, REJECTED
    rule_score_breakdown: Dict[str, Any]
    llm_explanation: str
    analyzed_at: str


class MemoryRetainRequest(BaseModel):
    bank_id: str = "pipelinemind-devops"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryRecallRequest(BaseModel):
    bank_id: str = "pipelinemind-devops"
    query: str
    limit: int = 5


class MemoryReflectRequest(BaseModel):
    bank_id: str = "pipelinemind-devops"
    query: str
    focus: Optional[str] = None


class AgentChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = "default-session"
    context: Optional[Dict[str, Any]] = None


class AgentChatResponse(BaseModel):
    response: str
    memories_used: List[Dict[str, Any]] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    reasoning: str
    provider: str
    model: str
    timestamp: str


class RollbackRequest(BaseModel):
    deployment_id: str
    target_version: Optional[str] = None
    reason: str = "Automated rollback triggered after health verification failure"


class RollbackResponse(BaseModel):
    success: bool
    deployment_id: str
    previous_stable_version: str
    current_status: str
    logs: List[str]
    executed_at: str


class Settings(BaseModel):
    groq_api_key: Optional[str] = ""
    groq_model: str = "openai/gpt-oss-120b"
    hindsight_api_url: Optional[str] = "http://localhost:8888"
    hindsight_api_key: Optional[str] = ""
    hindsight_bank_id: str = "pipelinemind-devops"
    simulation_mode: bool = True
