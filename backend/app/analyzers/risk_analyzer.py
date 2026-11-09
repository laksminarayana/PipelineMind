from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from backend.app.analyzers.diff_parser import DiffParser
from backend.app.hindsight.memory_manager import memory_manager
from backend.app.agent.groq_client import groq_client
from backend.app.database.connection import get_db


class DeploymentRiskAnalyzer:
    """
    Transparent rule-based scoring combined with Hindsight memory recall and LLM explanation.
    Does NOT claim heuristic scores are statistically calibrated probabilities.
    """

    def __init__(self):
        self.parser = DiffParser()
        self.memory = memory_manager
        self.groq = groq_client

    async def analyze(
        self,
        dockerfile_diff: str = "",
        k8s_diff: str = "",
        dependency_diff: str = "",
        db_config_diff: str = "",
        strategy: str = "rolling",
        commit_sha: str = "HEAD"
    ) -> Dict[str, Any]:
        # 1. Parse individual diffs
        docker_res = self.parser.parse_dockerfile(dockerfile_diff)
        k8s_res = self.parser.parse_k8s(k8s_diff)
        db_res = self.parser.parse_db_config(db_config_diff)
        dep_res = self.parser.parse_dependencies(dependency_diff)

        reasons = []
        reasons.extend(docker_res["findings"])
        reasons.extend(k8s_res["findings"])
        reasons.extend(db_res["findings"])
        reasons.extend(dep_res["findings"])

        # Base rule points
        base_points = (
            docker_res["weight"] +
            k8s_res["weight"] +
            db_res["weight"] +
            dep_res["weight"]
        )

        # Strategy risk adjustments
        strategy_adjustment = 0
        if strategy.lower() == "canary":
            strategy_adjustment = -10  # Canary mitigates blast radius
        elif strategy.lower() == "blue-green":
            strategy_adjustment = -5
        elif strategy.lower() == "recreate":
            strategy_adjustment = 15

        # 2. Check Hindsight for historical incident similarity
        diff_summary = f"{dockerfile_diff} {k8s_diff} {db_config_diff} {dependency_diff}".strip()
        search_query = diff_summary if diff_summary else "database kubernetes config change"
        recalled_memories = self.memory.recall_similar_incidents(query=search_query, limit=3)

        history_multiplier = 0
        related_incidents = []
        for mem in recalled_memories:
            meta = mem.get("metadata", {})
            similarity = mem.get("similarity_score", 0.0)
            if similarity > 0.2:
                related_incidents.append(mem)
                if "database" in mem.get("content", "").lower() and db_res["findings"]:
                    history_multiplier += 20
                    reasons.append(
                        f"Hindsight Alert: Similar database change previously caused incident '{meta.get('incident_id', 'INC')}'"
                    )
                elif similarity > 0.4:
                    history_multiplier += 10

        # Calculate final 0 - 100 bounded score
        raw_score = 15 + base_points + strategy_adjustment + history_multiplier
        final_score = max(5, min(98, raw_score))

        # Risk Category & Decision
        if final_score < 40:
            category = "Low"
            decision = "APPROVED"
        elif final_score < 70:
            category = "Medium"
            decision = "REVIEW_REQUIRED"
        else:
            category = "High"
            decision = "REJECTED"

        # Preventive actions
        preventive_actions = []
        if db_res["findings"]:
            preventive_actions.append("Verify database credentials exist in Kubernetes secret 'db-secret'")
            preventive_actions.append("Run network ping test to database endpoint prior to traffic cutover")
        if k8s_res["findings"]:
            preventive_actions.append("Ensure resource limits (memory: 512Mi, cpu: 500m) are declared in deployment manifest")
        if docker_res["findings"]:
            preventive_actions.append("Switch Dockerfile execution to non-root UID 10001 (USER appuser)")
        if not preventive_actions:
            preventive_actions.append("Proceed with standard automated canary verification on 10% traffic.")

        # 3. Generate LLM explanation via Groq
        rule_breakdown = {
            "base_heuristics": 15,
            "dockerfile_findings": docker_res["findings"],
            "dockerfile_weight": docker_res["weight"],
            "k8s_findings": k8s_res["findings"],
            "k8s_weight": k8s_res["weight"],
            "db_findings": db_res["findings"],
            "db_weight": db_res["weight"],
            "strategy_adjustment": strategy_adjustment,
            "hindsight_memory_penalty": history_multiplier,
            "total_score": final_score
        }

        explanation_prompt = (
            f"Explain this deployment risk score: {final_score}/100 ({category} Risk, Decision: {decision}).\n"
            f"Reasons: {reasons}\n"
            f"Historical incidents recalled from Hindsight: {len(related_incidents)}\n"
            f"Deployment Strategy: {strategy}\n"
            "Provide a concise, professional 3-sentence DevOps risk summary."
        )

        llm_res = await self.groq.generate_completion(
            messages=[
                {"role": "system", "content": "You are a DevOps Risk Evaluator for CI/CD pipelines."},
                {"role": "user", "content": explanation_prompt}
            ],
            temperature=0.2
        )

        return {
            "risk_score": final_score,
            "risk_category": category,
            "reasons": reasons if reasons else ["Clean diff with no high-risk infrastructure heuristics detected."],
            "related_incidents": related_incidents,
            "recommended_preventive_actions": preventive_actions,
            "deployment_decision": decision,
            "rule_score_breakdown": rule_breakdown,
            "llm_explanation": llm_res["content"],
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }


risk_analyzer = DeploymentRiskAnalyzer()
