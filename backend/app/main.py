import os
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from backend.app.database.schema import init_db, seed_initial_data_if_empty
from backend.app.api.routes import router as api_router
from backend.app.services.metrics_service import PROMETHEUS_HTTP_LATENCY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("PipelineMind")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite schema and initial baseline seed
    logger.info("Initializing PipelineMind AI backend services...")
    init_db()
    seed_initial_data_if_empty()
    logger.info("Database initialized. Ready to process deployments and Hindsight memories.")
    yield
    logger.info("PipelineMind AI backend shutting down gracefully.")


app = FastAPI(
    title="PipelineMind AI API",
    description="Self-learning DevOps pipeline agent with optional Groq and Hindsight integrations plus a local demo memory bank.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(api_router, prefix="/api")


@app.middleware("http")
async def record_http_latency(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    endpoint = getattr(route, "path", "unmatched")
    PROMETHEUS_HTTP_LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
    return response


@app.get("/")
async def root():
    return {
        "project": "PipelineMind AI",
        "tagline": "Self-Learning DevOps Pipeline Agent with Hindsight memory integration",
        "status": "operational",
        "docs": "/api/docs"
    }


# Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred.", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=True)
