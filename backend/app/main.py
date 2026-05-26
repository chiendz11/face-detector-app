from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
import redis
from sqlalchemy import text

from app.api.endpoints_admin import router as admin_router
from app.api.endpoints_auth import router as auth_router
from app.api.endpoints_vision import router as vision_router
from app.core.config import settings
from app.db import engine

HTTP_REQUESTS_TOTAL = Counter(
    "face_detector_http_requests_total",
    "Total HTTP requests handled by the Face Detector backend.",
    ["method", "path", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "face_detector_http_request_duration_seconds",
    "HTTP request duration in seconds for the Face Detector backend.",
    ["method", "path", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "face_detector_http_requests_in_progress",
    "HTTP requests currently in progress for the Face Detector backend.",
)
HTTP_ERRORS_TOTAL = Counter(
    "face_detector_http_errors_total",
    "Total HTTP requests that returned 5xx from the Face Detector backend.",
    ["method", "path", "status_code"],
)
DEPENDENCY_HEALTH_STATUS = Gauge(
    "face_detector_dependency_health_status",
    "Dependency health status where 1 is healthy, 0 is unhealthy, and -1 is unknown.",
    ["dependency"],
)

DEPENDENCY_HEALTH_STATUS.labels("application").set(1)
DEPENDENCY_HEALTH_STATUS.labels("database").set(-1)
DEPENDENCY_HEALTH_STATUS.labels("redis").set(-1)

app = FastAPI(title=settings.app_name)


@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    start = perf_counter()
    status_code = "500"
    HTTP_REQUESTS_IN_PROGRESS.inc()

    try:
        response = await call_next(request)
        status_code = str(response.status_code)
        return response
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", None) or "__unmatched__"
        duration = perf_counter() - start
        HTTP_REQUESTS_TOTAL.labels(request.method, path, status_code).inc()
        if status_code.startswith("5"):
            HTTP_ERRORS_TOTAL.labels(request.method, path, status_code).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(request.method, path, status_code).observe(duration)
        HTTP_REQUESTS_IN_PROGRESS.dec()


app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(vision_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)


@app.get("/health")
def healthcheck() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "embedding_provider": settings.embedding_provider,
        "model_name": settings.model_name,
        "model_version": settings.model_version,
        "embedding_dimensions": settings.embedding_dimensions,
        "match_threshold": settings.match_threshold,
    }


@app.get("/ready")
def readiness():
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
    }
    healthy = all(checks.values())

    for dependency, status in checks.items():
        DEPENDENCY_HEALTH_STATUS.labels(dependency).set(1 if status else 0)
    DEPENDENCY_HEALTH_STATUS.labels("application").set(1)

    payload = {
        "status": "ready" if healthy else "not_ready",
        "dependencies": checks,
    }
    if healthy:
        return payload
    return JSONResponse(payload, status_code=503)


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _check_database() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _check_redis() -> bool:
    try:
        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        return bool(client.ping())
    except Exception:
        return False
