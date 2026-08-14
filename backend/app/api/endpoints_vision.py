import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import get_recognition_service
from app.models.schemas import RecognitionResponse
from app.services.recognition_service import RecognitionService
from app.utils.structured_logging import log_event

router = APIRouter(prefix="/vision", tags=["vision"])
logger = logging.getLogger(__name__)


@router.get("/health")
def vision_health() -> dict:
    return {"status": "ok", "scope": "vision"}


@router.post("/recognize")
async def recognize_face(
    file: UploadFile = File(...),
    device_name: str | None = Form(default=None),
    recognition_service: RecognitionService = Depends(get_recognition_service),
) -> RecognitionResponse:
    image_bytes = await file.read()
    filename = file.filename or "uploaded-face.jpg"
    log_event(
        logger,
        logging.INFO,
        "vision_recognition_request_received",
        filename=filename,
        device_name=device_name,
        image_size_bytes=len(image_bytes),
    )

    try:
        return recognition_service.recognize_face(
            filename=filename,
            image_bytes=image_bytes,
            device_name=device_name,
        )
    except ValueError as exc:
        log_event(
            logger,
            logging.WARNING,
            "vision_recognition_request_rejected",
            filename=filename,
            device_name=device_name,
            error_type=type(exc).__name__,
            error=exc,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        log_event(
            logger,
            logging.ERROR,
            "vision_recognition_request_failed",
            filename=filename,
            device_name=device_name,
            error_type=type(exc).__name__,
            error=exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
