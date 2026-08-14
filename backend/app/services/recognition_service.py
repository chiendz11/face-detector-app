import logging
import time
from time import perf_counter
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db_models import RecognitionEvent
from app.models.schemas import RecognitionResponse, RecognitionResult
from app.services.deepface_service import DeepFaceService
from app.services.minio_service import MinioService
from app.services.vector_search_service import VectorSearchService
from app.utils.resilience import CircuitBreaker, retry_operation
from app.utils.structured_logging import log_event

logger = logging.getLogger(__name__)

DB_CIRCUIT_BREAKER = CircuitBreaker(
    failure_threshold=settings.db_circuit_failure_threshold,
    recovery_timeout=settings.db_circuit_recovery_seconds,
    exceptions=(Exception,),
)


class RecognitionService:
    def __init__(
        self,
        deepface_service: DeepFaceService,
        vector_search_service: VectorSearchService,
        minio_service: MinioService,
        db: Session | None = None,
    ) -> None:
        self.deepface_service = deepface_service
        self.vector_search_service = vector_search_service
        self.minio_service = minio_service
        self.db = db

    def recognize_face(
        self,
        *,
        filename: str,
        image_bytes: bytes,
        device_name: str | None = None,
    ) -> RecognitionResponse:
        if not filename:
            raise ValueError("filename must not be empty")

        start = perf_counter()
        stage = "normalize"

        try:
            normalized_device_name = self._normalize_segment(device_name or "unknown-device")
            normalized_filename = self._normalize_segment(filename)
            object_name = f"{normalized_device_name}/{normalized_filename}"
            log_event(
                logger,
                logging.INFO,
                "recognition_started",
                device_name=device_name,
                filename=filename,
                object_name=object_name,
                image_size_bytes=len(image_bytes),
            )
            stage = "embedding"
            embedding = self.deepface_service.embed_face(image_bytes)
            stage = "vector_search"
            match_payload = self.vector_search_service.search_similar_face(embedding)
            stage = "snapshot_upload"
            snapshot_url = self.minio_service.upload_snapshot(object_name, image_bytes)
            matched = match_payload["match"] is not None
            confidence = float(match_payload["score"])

            event = RecognitionEvent(
                employee_code=match_payload["match"],
                matched=matched,
                confidence=confidence,
                device_name=device_name,
                filename=filename,
                snapshot_url=snapshot_url,
            )
            stage = "event_save"
            self._save_event(event)

            if matched:
                status = "granted"
                message = f"Face matched employee {match_payload['match']}."
            else:
                status = "rejected"
                message = "Face was processed but no employee matched the threshold."

            log_event(
                logger,
                logging.INFO,
                "recognition_completed",
                device_name=device_name,
                filename=filename,
                status=status,
                matched=matched,
                employee_code=match_payload["match"],
                confidence=confidence,
                duration_ms=round((perf_counter() - start) * 1000, 3),
            )
            return RecognitionResponse(
                device_name=device_name,
                filename=filename,
                status=status,
                message=message,
                result=RecognitionResult(
                    matched=matched,
                    employee_code=match_payload["match"],
                    confidence=confidence,
                    snapshot_url=snapshot_url,
                ),
            )
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "recognition_failed",
                device_name=device_name,
                filename=filename,
                stage=stage,
                error_type=type(exc).__name__,
                error=exc,
                duration_ms=round((perf_counter() - start) * 1000, 3),
            )
            raise

    def _save_event(self, event: RecognitionEvent) -> None:
        if self.db is None:
            log_event(
                logger,
                logging.INFO,
                "recognition_event_skipped",
                reason="database_session_unavailable",
                employee_code=event.employee_code,
                matched=bool(event.matched),
                confidence=float(event.confidence),
            )
            return

        if event.matched and event.employee_code:
            event.dedupe_key = self._build_dedupe_key(event.employee_code)

        self.db.add(event)

        # Flush first so that constraint violations (e.g. duplicate dedupe_key)
        # raise IntegrityError here, before retry logic can wrap the second
        # attempt in PendingRollbackError (SQLAlchemy 2.x behaviour).
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            if "dedupe_key" in str(exc).lower():
                log_event(
                    logger,
                    logging.INFO,
                    "recognition_event_deduplicated",
                    employee_code=event.employee_code,
                    dedupe_key=event.dedupe_key,
                )
                return
            raise

        @retry_operation(
            max_attempts=settings.db_retry_attempts,
            initial_delay=settings.db_retry_backoff_seconds,
        )
        def attempt_commit() -> None:
            self.db.commit()

        try:
            DB_CIRCUIT_BREAKER.call(attempt_commit)
            log_event(
                logger,
                logging.INFO,
                "recognition_event_saved",
                employee_code=event.employee_code,
                matched=bool(event.matched),
                confidence=float(event.confidence),
                dedupe_key=event.dedupe_key,
            )
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _build_dedupe_key(employee_code: str) -> str:
        normalized_code = employee_code.strip().upper()
        window = settings.dedupe_window_seconds
        bucket = int(time.time() // window)
        return f"{normalized_code}:{bucket}"

    @staticmethod
    def _normalize_segment(value: str) -> str:
        sanitized = "".join(
            character if character.isalnum() or character in {"-", "_", "."} else "-"
            for character in value.strip()
        )
        sanitized = sanitized.strip("-")

        if not sanitized:
            raise ValueError("path segment must not be empty")

        return sanitized
