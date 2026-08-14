import logging

from app.worker.celery_app import celery_app
from app.utils.structured_logging import log_event

logger = logging.getLogger(__name__)


@celery_app.task
def rebuild_face_embeddings() -> dict:
    log_event(logger, logging.INFO, "celery_task_started", task_name="rebuild_face_embeddings")
    result = {"status": "queued", "message": "Implement face re-indexing here."}
    log_event(
        logger,
        logging.INFO,
        "celery_task_completed",
        task_name="rebuild_face_embeddings",
        status=result["status"],
    )
    return result
