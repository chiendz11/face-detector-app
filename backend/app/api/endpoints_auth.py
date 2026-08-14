import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_auth_service
from app.models.schemas import LoginRequest, Token
from app.services.auth_service import AuthService
from app.utils.structured_logging import log_event

router = APIRouter(prefix="/auth", tags=["auth"])
AUTH_SCHEME = "bearer"
logger = logging.getLogger(__name__)


@router.post("/login", response_model=Token)
def login(
    credentials: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    if not auth_service.authenticate_user(
        credentials.username,
        credentials.password,
    ):
        log_event(
            logger,
            logging.WARNING,
            "login_failed",
            username=credentials.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_service.create_access_token(subject=credentials.username)
    log_event(
        logger,
        logging.INFO,
        "login_succeeded",
        username=credentials.username,
        token_type=AUTH_SCHEME,
    )
    return Token(access_token=token, token_type=AUTH_SCHEME)
