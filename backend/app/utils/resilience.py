from __future__ import annotations

import logging
import time
from functools import wraps
from threading import Lock

from app.utils.structured_logging import log_event


logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.exceptions = exceptions
        self.failure_count = 0
        self.state: str = "closed"
        self._reopened_at: float | None = None
        self._lock = Lock()

    def call(self, func, *args, **kwargs):
        with self._lock:
            now = time.monotonic()
            if self.state == "open":
                if self._reopened_at is not None and now < self._reopened_at + self.recovery_timeout:
                    log_event(
                        logger,
                        logging.WARNING,
                        "circuit_breaker_rejected",
                        operation=getattr(func, "__name__", "unknown"),
                        state=self.state,
                        failure_count=self.failure_count,
                        recovery_timeout_seconds=self.recovery_timeout,
                    )
                    raise RuntimeError("Circuit breaker is open; service temporarily unavailable")
                self.state = "half_open"
                log_event(
                    logger,
                    logging.INFO,
                    "circuit_breaker_half_open",
                    operation=getattr(func, "__name__", "unknown"),
                    failure_count=self.failure_count,
                )

        try:
            result = func(*args, **kwargs)
        except self.exceptions as exc:
            with self._lock:
                self.failure_count += 1
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    self._reopened_at = now
                    log_event(
                        logger,
                        logging.ERROR,
                        "circuit_breaker_opened",
                        operation=getattr(func, "__name__", "unknown"),
                        failure_count=self.failure_count,
                        failure_threshold=self.failure_threshold,
                        recovery_timeout_seconds=self.recovery_timeout,
                        error_type=type(exc).__name__,
                        error=exc,
                    )
                else:
                    log_event(
                        logger,
                        logging.WARNING,
                        "circuit_breaker_failure_recorded",
                        operation=getattr(func, "__name__", "unknown"),
                        failure_count=self.failure_count,
                        failure_threshold=self.failure_threshold,
                        error_type=type(exc).__name__,
                        error=exc,
                    )
            raise
        else:
            with self._lock:
                previous_state = self.state
                previous_failure_count = self.failure_count
                self.failure_count = 0
                self.state = "closed"
                self._reopened_at = None
                if previous_state != "closed" or previous_failure_count:
                    log_event(
                        logger,
                        logging.INFO,
                        "circuit_breaker_closed",
                        operation=getattr(func, "__name__", "unknown"),
                        previous_state=previous_state,
                        previous_failure_count=previous_failure_count,
                    )
            return result

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper


def retry_operation(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    multiplier: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> callable:
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_error: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_error = exc
                    if attempt == max_attempts:
                        log_event(
                            logger,
                            logging.ERROR,
                            "operation_retry_exhausted",
                            operation=getattr(func, "__name__", "unknown"),
                            attempt=attempt,
                            max_attempts=max_attempts,
                            error_type=type(exc).__name__,
                            error=exc,
                        )
                        raise
                    log_event(
                        logger,
                        logging.WARNING,
                        "operation_retry_scheduled",
                        operation=getattr(func, "__name__", "unknown"),
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay_seconds=delay,
                        error_type=type(exc).__name__,
                        error=exc,
                    )
                    time.sleep(delay)
                    delay *= multiplier
            raise last_error  # pragma: no cover

        return wrapper

    return decorate
