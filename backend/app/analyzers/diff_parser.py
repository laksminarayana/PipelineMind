import re
from typing import Dict, Any, List


class DiffParser:
    """
    Parses configuration and infrastructure diffs for risk signals.
    """

    @staticmethod
    def parse_dockerfile(diff: str) -> Dict[str, Any]:
        findings = []
        risk_weight = 0

        if not diff:
            return {"findings": findings, "weight": risk_weight}

        lines = diff.splitlines()
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("+") and not line_str.startswith("+++"):
                content = line_str[1:].strip()
                if re.search(r"USER\s+root", content, re.IGNORECASE):
                    findings.append("Container configured to run as root user")
                    risk_weight += 20
                if re.search(r":latest", content):
                    findings.append("Using unpinned ':latest' image tag in Dockerfile")
                    risk_weight += 15
                if re.search(r"curl.*\|.*sh", content):
                    findings.append("Unsafe curl pipe to shell execution detected")
                    risk_weight += 25
                if re.search(r"EXPOSE\s+(22|3306|5432|27017)", content):
                    findings.append("Exposing direct database/SSH port in application container")
                    risk_weight += 15

        return {"findings": findings, "weight": risk_weight}

    @staticmethod
    def parse_k8s(diff: str) -> Dict[str, Any]:
        findings = []
        risk_weight = 0

        if not diff:
            return {"findings": findings, "weight": risk_weight}

        lines = diff.splitlines()
        added_text = " ".join([l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")])

        if "privileged: true" in added_text.lower():
            findings.append("Privileged container mode enabled in Kubernetes manifest")
            risk_weight += 30

        if "hostnetwork: true" in added_text.lower():
            findings.append("Pod hostNetwork enabled (security risk)")
            risk_weight += 25

        if "resources:" not in diff and ("kind: Deployment" in diff or "spec:" in diff):
            findings.append("No CPU/Memory resource requests and limits specified")
            risk_weight += 15

        if "livenessprobe" not in diff.lower() and "readinessprobe" not in diff.lower() and "containers:" in diff:
            findings.append("Missing Kubernetes liveness and readiness health probes")
            risk_weight += 15

        return {"findings": findings, "weight": risk_weight}

    @staticmethod
    def parse_db_config(diff: str) -> Dict[str, Any]:
        findings = []
        risk_weight = 0

        if not diff:
            return {"findings": findings, "weight": risk_weight}

        diff_lower = diff.lower()
        if "db_host" in diff_lower or "database_url" in diff_lower or "postgres" in diff_lower:
            findings.append("Database host/endpoint connection string modified")
            risk_weight += 25

        if "password" in diff_lower and ("plain" in diff_lower or "=" in diff_lower):
            findings.append("Potential plaintext database credentials in configuration diff")
            risk_weight += 30

        if "pool_size" in diff_lower or "max_connections" in diff_lower:
            findings.append("Database connection pool sizing altered")
            risk_weight += 10

        return {"findings": findings, "weight": risk_weight}

    @staticmethod
    def parse_dependencies(diff: str) -> Dict[str, Any]:
        findings = []
        risk_weight = 0

        if not diff:
            return {"findings": findings, "weight": risk_weight}

        lines = diff.splitlines()
        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                if any(pkg in line.lower() for pkg in ["cryptography", "openssl", "django", "fastapi", "spring"]):
                    findings.append("Core framework or cryptography package dependency modified")
                    risk_weight += 15
                    break

        return {"findings": findings, "weight": risk_weight}
