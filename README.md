# PipelineMind AI

PipelineMind is a self-learning DevOps pipeline demonstration. It combines a React dashboard, FastAPI API, SQLite deployment history, a Hindsight-compatible memory layer, optional Groq completions, risk heuristics, and simulated delivery workflows.

> **Demo and safety notice:** Pipeline execution, telemetry, pod details, and deployment strategies are simulated. The app does not connect to or change a production Kubernetes cluster. Risk scores are transparent heuristics, not calibrated failure probabilities. Verify AI recommendations before acting.

## Requirements

- Python 3.10+ (Python 3.11 recommended)
- Node.js 20+ and pnpm 9+
- Optional: Docker Desktop with Compose
- Optional: Groq API key and a Hindsight server/API key

## Run locally on Windows

Open two PowerShell terminals from the project directory.

### Backend

```powershell
cd G:\pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend initializes the SQLite database under `backend\data\` at startup and seeds an initial successful deployment. Useful endpoints:

- API documentation: <http://localhost:8000/api/docs>
- Health: <http://localhost:8000/api/health>
- Prometheus metrics: <http://localhost:8000/api/prometheus>

### Frontend

```powershell
cd G:\pipeline\frontend
pnpm install
pnpm dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to the backend on port 8000.

To run backend tests:

```powershell
cd G:\pipeline
python -m pytest backend\tests -q
```

To create a production frontend bundle:

```powershell
cd G:\pipeline\frontend
pnpm build
```

## Provider configuration

The app runs without external credentials in local simulation mode. Use the dashboard's **Settings** page to configure the optional Groq model and API key or Hindsight server URL, API key, and bank ID. Turn off **Simulation mode** in Settings to use Groq. The default Groq model is `openai/gpt-oss-120b`.

The Hindsight adapter uses the official `hindsight_client` SDK if it is installed and configured. Otherwise, it runs a clearly labeled local SQLite demo memory engine with retain, recall, and reflect operations. The local engine is useful for demonstrations but is not a connection to Hindsight Cloud. Groq calls are also optional; simulation mode uses the local response implementation.

For environment-based configuration, copy `.env.example` to `.env` and set values as needed. Do not commit `.env` or use production credentials in a shared demo. Compose passes these variables to the backend. Settings entered in the dashboard are stored in the local SQLite database.

## Demonstration

From the Overview or CI/CD Pipeline page, run the three Hindsight learning steps in order:

1. **Learn from a failure** — simulate a database connection configuration failure and retain an incident.
2. **Recall the incident** — replay a similar change and review the historical recommendation and risk.
3. **Deploy the fix** — apply the simulated corrected configuration and show the successful outcome.

The pipeline page also offers successful and controlled-failure runs. These are demonstrations only; they do not issue shell commands or change a cluster.

## Docker Compose

From the repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Services:

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000/api/docs>
- Prometheus: <http://localhost:9090>
- Grafana: <http://localhost:3000> (default demo login `admin` / `admin`)

Change `GRAFANA_ADMIN_PASSWORD` in `.env` before exposing Grafana beyond a local development machine. Compose persists SQLite, Prometheus, and Grafana data in named volumes. Stop services with `docker compose down`; `docker compose down -v` also removes the data volumes.

## GitHub Actions and GHCR

`.github/workflows/ci-cd.yml` runs backend tests, builds the frontend, and scans the repository with Trivy for HIGH/CRITICAL vulnerabilities. On pushes to `main` and version tags, it builds and publishes backend and frontend images to GitHub Container Registry using the built-in `GITHUB_TOKEN`.

To enable the workflow:

1. Push the repository to GitHub and enable Actions.
2. Ensure the repository grants the workflow `packages: write` permission.
3. For version-tag deployment handoff, create a GitHub environment named `production` and configure required reviewers in its protection rules.
4. Update the image references in `infrastructure/kubernetes/app.yaml` to your GHCR owner/repository.

The protected job is an approval-gated handoff only. It intentionally does not authenticate to or modify a production cluster.

## Kubernetes

The manifests in `infrastructure/kubernetes/app.yaml` include a ConfigMap, optional Secret references, a persistent volume claim for SQLite, backend and frontend Deployments and Services, resource limits, and HTTP health probes.

After updating the image names to your GHCR namespace and pushing the images:

```powershell
kubectl apply -f infrastructure\kubernetes\app.yaml
kubectl get deployments,services,pods
kubectl port-forward service/pipelinemind-frontend 8080:80
```

Open <http://localhost:8080>. Create credentials separately; for example, use `kubectl create secret generic pipelinemind-secrets --from-literal=GROQ_API_KEY=... --from-literal=HINDSIGHT_API_KEY=...`. Omit keys not needed for the local demo. Review storage-class availability, ingress, network policy, image references, and secrets handling before using a cluster. No Kubernetes commands are run by the application itself.

## Monitoring

The UI clearly labels demonstration telemetry as simulated. The FastAPI service exposes Prometheus-format metrics at `/api/prometheus`; `infrastructure/prometheus/prometheus.yml` scrapes it. Grafana provisions that data source and the dashboard in `infrastructure/grafana/`.

## Project layout

```text
backend/                 FastAPI API, SQLite services, analyzer, agent and memory adapter
backend/tests/            API, memory and risk analyzer tests
frontend/                 React + Vite dashboard
infrastructure/
  grafana/                Datasource, dashboard provisioning and dashboard JSON
  kubernetes/              Kubernetes app manifests
  prometheus/              Prometheus scrape configuration
.github/workflows/         Tests, Trivy scan, container publishing and approval handoff
Dockerfile                 Backend image
docker-compose.yml         Local app and observability stack
```

## Five-minute presentation outline

1. **0:00–0:40 — Problem:** recurring deployment failures are costly when teams lose operational context.
2. **0:40–1:20 — Product:** show the dashboard, deployment history, and health/telemetry view; clarify the demo data is simulated.
3. **1:20–2:30 — Learn:** run demo step 1 and show the database incident and retained memory.
4. **2:30–3:30 — Recall:** run step 2 and point out the similar historical issue, recommendation, and heuristic risk warning.
5. **3:30–4:20 — Improve:** run step 3 and show the corrected successful deployment and memory history.
6. **4:20–5:00 — Architecture and next steps:** explain FastAPI, SQLite, optional Groq/Hindsight integration, Prometheus/Grafana, and the approval-gated CI workflow. Emphasize that the demo does not perform production deployments.
