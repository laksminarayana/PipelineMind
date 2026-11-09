from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.agent.groq_client import groq_client
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.database.connection import get_db


class DevOpsAgent:
    """
    Self-learning DevOps AI Agent powered by Groq and Vectorize Hindsight memory.
    """

    def __init__(self):
        self.groq = groq_client
        self.memory = memory_manager

    async def analyze_incident(
        self,
        deployment_id: str,
        stage: str,
        error_message: str,
        config_changes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a new pipeline failure:
        1. Retrieve similar historical incidents using Hindsight.
        2. Pass the retrieved context to Groq (or fallback).
        3. Generate root-cause explanation and historical fix recommendation.
        """
        # Step 1: Recall similar incidents from Hindsight
        recall_query = f"{stage} {error_message} {config_changes or ''}"
        recalled_memories = self.memory.recall_similar_incidents(query=recall_query, limit=3)
        reflection = self.memory.reflect_on_incident(query=recall_query)

        # Step 2: Build contextual prompt
        historical_context = ""
        if recalled_memories:
            historical_context += "HISTORICAL INCIDENTS RECALLED FROM HINDSIGHT MEMORY:\n"
            for idx, m in enumerate(recalled_memories, 1):
                meta = m.get("metadata", {})
                historical_context += (
                    f"[{idx}] Incident ID: {meta.get('incident_id', 'Unknown')}\n"
                    f"    Stage: {meta.get('pipeline_stage')}\n"
                    f"    Past Error: {meta.get('error_message')}\n"
                    f"    Root Cause: {meta.get('root_cause')}\n"
                    f"    Remediation Applied: {meta.get('corrective_action')}\n"
                    f"    Resolved Successfully: {meta.get('fix_succeeded')}\n"
                    f"    Similarity Score: {m.get('similarity_score', 0.0)}\n\n"
                )
        else:
            historical_context = "No previous incidents matching this error pattern were found in Hindsight memory.\n"

        system_prompt = (
            "You are PipelineMind AI, a Senior Principal DevOps Engineer and Site Reliability Architect.\n"
            "You diagnose CI/CD failures and recommend precise, actionable remediations.\n"
            "CRITICAL: Always reference relevant historical incidents recalled from Hindsight memory.\n"
            "If a past incident solved this issue, highlight that historical resolution clearly."
        )

        user_prompt = (
            f"Deployment ID: {deployment_id}\n"
            f"Failed Pipeline Stage: {stage}\n"
            f"Error Message: {error_message}\n"
            f"Infrastructure Changes / Diff: {config_changes or 'None provided'}\n\n"
            f"{historical_context}\n"
            f"Hindsight Reflection Synthesis: {reflection.get('synthesis', '')}\n\n"
            "Please provide:\n"
            "1. Root Cause Analysis\n"
            "2. Comparison with Past Incidents (if any)\n"
            "3. Step-by-Step Corrective Action to fix the pipeline"
        )

        llm_response = await self.groq.generate_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )

        return {
            "root_cause_explanation": llm_response["content"],
            "recalled_memories": recalled_memories,
            "reflection": reflection,
            "provider": llm_response["provider"],
            "model": llm_response["model"],
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }

    async def chat(
        self,
        user_message: str,
        conversation_id: str = "default",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Chat with AI assistant using Hindsight memory context when relevant.
        """
        # Search Hindsight memory for context
        recalled = self.memory.recall_similar_incidents(query=user_message, limit=4)
        
        memory_snippets = []
        for m in recalled:
            memory_snippets.append({
                "id": m.get("id"),
                "incident_id": m.get("incident_id"),
                "content": m.get("content"),
                "similarity_score": m.get("similarity_score"),
                "metadata": m.get("metadata")
            })

        system_prompt = (
            "You are PipelineMind AI, an autonomous DevOps assistant with persistent memory.\n"
            "You answer questions about deployment health, previous failures, CI/CD pipeline bottlenecks, "
            "and Kubernetes configurations.\n"
            "Use the provided Hindsight memory records to ground your answers in actual team history."
        )

        mem_text = ""
        if memory_snippets:
            mem_text = "\nRELEVANT HINDSIGHT DEVOPS MEMORIES:\n" + "\n".join(
                [f"- [Score: {m['similarity_score']}] {m['content']}" for m in memory_snippets]
            )

        messages = [
            {"role": "system", "content": system_prompt + mem_text},
            {"role": "user", "content": user_message}
        ]

        llm_result = await self.groq.generate_completion(messages=messages, temperature=0.2)

        # Generate smart follow-up suggestions
        suggested_actions = [
            "Why did my last deployment fail?",
            "Have we experienced this issue before?",
            "What did the agent learn from previous incidents?",
            "Should I deploy this version?"
        ]

        return {
            "response": llm_result["content"],
            "memories_used": memory_snippets,
            "suggested_actions": suggested_actions,
            "reasoning": f"Synthesized response using {len(memory_snippets)} historical memory records via Hindsight.",
            "provider": llm_result["provider"],
            "model": llm_result["model"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


devops_agent = DevOpsAgent()
