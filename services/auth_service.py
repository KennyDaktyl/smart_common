import logging
from datetime import timedelta

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.tasks.email_tasks import (
    send_confirmation_email_task,
    send_password_reset_email_task,
)
from smart_common.core.config import settings
from smart_common.core.security import (
    TokenType,
    create_access_token,
    create_action_token,
    create_refresh_token,
    decode_and_validate_token,
    hash_password,
    verify_password,
)
from smart_common.enums.user import UserRole
from smart_common.models.user import User
from smart_common.repositories.user import UserRepository
from smart_common.schemas.user_schema import UserCreate

logger = logging.getLogger(__name__)


class AuthService:
    EMAIL_TOKEN_EXPIRE = timedelta(hours=24)
    PASSWORD_RESET_EXPIRE = timedelta(hours=1)

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> tuple[str, str]:
        user = self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is not active")

        logger.info("User login succeeded id=%s email=%s", user.id, user.email)

        return self._build_tokens(user)

    def refresh(self, refresh_token: str) -> tuple[str, str]:
        payload = decode_and_validate_token(refresh_token, TokenType.REFRESH)
        if not payload:
            raise HTTPException(
                status_code=401, detail="Invalid or expired refresh token"
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Refresh token is malformed")

        user = self.user_repo.get_by_id(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        logger.info("Refresh token rotated for user id=%s", user.id)

        return self._build_tokens(user)

    # ------------------------------------------------------------------
    # REGISTRATION
    # ------------------------------------------------------------------

    def register(self, payload: UserCreate) -> User:
        email = self._normalize_email_or_422(payload.email)
        logger.info("Register attempt email=%s", email)

        user = self.user_repo.get_by_email(email)

        # --------------------------------------------------
        # USER EXISTS
        # --------------------------------------------------
        if user:
            if user.is_active:
                logger.warning(
                    "Register blocked - active user exists email=%s",
                    email,
                )
                raise HTTPException(
                    status_code=400,
                    detail="User with this email already exists",
                )

            # user exists but inactive -> resend confirmation
            logger.info(
                "User exists but inactive - resending confirmation email email=%s",
                email,
            )

            token = create_action_token(
                {"sub": str(user.id)},
                expires_delta=self.EMAIL_TOKEN_EXPIRE,
            )
            self._queue_confirmation_email(user.email, token)
            return user

        # --------------------------------------------------
        # NEW USER
        # --------------------------------------------------
        try:
            user = self.user_repo.model(
                email=email,
                password_hash=hash_password(payload.password),
                role=UserRole.CLIENT,
                is_active=False,
            )

            self.user_repo.session.add(user)
            self.user_repo.session.flush()  # get ID

            token = create_action_token(
                {"sub": str(user.id)},
                expires_delta=self.EMAIL_TOKEN_EXPIRE,
            )

            self._queue_confirmation_email(user.email, token)

            self.user_repo.session.commit()
            logger.info("User registered id=%s email=%s", user.id, user.email)

            return user

        except IntegrityError:
            self.user_repo.session.rollback()
            logger.warning(
                "IntegrityError - duplicate email email=%s",
                email,
            )
            raise HTTPException(
                status_code=400,
                detail="User with this email already exists",
            )

        except HTTPException:
            self.user_repo.session.rollback()
            raise

        except Exception:
            self.user_repo.session.rollback()
            logger.exception(
                "Unexpected error during registration email=%s",
                email,
            )
            raise HTTPException(
                status_code=500,
                detail="Registration failed. Please try again later.",
            )

    # ------------------------------------------------------------------
    # EMAIL CONFIRMATION
    # ------------------------------------------------------------------

    def confirm_email(self, token: str) -> None:
        payload = decode_and_validate_token(token, TokenType.ACTION)
        if not payload:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Token missing subject")

        user = self.user_repo.get_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_active:
            return

        logger.info("Confirming email for user id=%s", user.id)
        self.user_repo.activate_user(user)

    # ------------------------------------------------------------------
    # PASSWORD RESET
    # ------------------------------------------------------------------

    def request_password_reset(self, email: str) -> None:
        user = self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            logger.info(
                "Password reset skipped for email=%s (user not found or inactive)",
                email,
            )
            return

        token = create_action_token(
            {"sub": str(user.id)},
            expires_delta=self.PASSWORD_RESET_EXPIRE,
        )
        try:
            send_password_reset_email_task.delay(user.email, token)
        except Exception:
            logger.exception("Failed to queue password reset email for %s", user.email)
            return
        logger.info("Password reset token generated for user id=%s", user.id)
        return token

    def reset_password(self, token: str, new_password: str) -> None:
        payload = decode_and_validate_token(token, TokenType.ACTION)
        if not payload:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Token missing subject")

        user = self.user_repo.get_by_id(int(user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        self.user_repo.update_password(user, hash_password(new_password))
        logger.info("Password reset confirmed for user id=%s", user.id)

    # ------------------------------------------------------------------
    # TOKENS
    # ------------------------------------------------------------------

    def _build_tokens(self, user: User) -> tuple[str, str]:
        access_token = create_access_token(
            {
                "sub": str(user.id),
                "role": user.role.value,
            }
        )
        refresh_token = create_refresh_token({"sub": str(user.id)})
        return access_token, refresh_token

    @staticmethod
    def _normalize_email_or_422(email: str) -> str:
        try:
            validated = validate_email(str(email), check_deliverability=False)
            return validated.normalized
        except EmailNotValidError as exc:
            logger.warning("Rejected invalid email during registration email=%s", email)
            raise HTTPException(
                status_code=422, detail="Invalid email address format"
            ) from exc

    @staticmethod
    def _queue_confirmation_email(email: str, token: str) -> None:
        try:
            send_confirmation_email_task.delay(email, token)
        except Exception as exc:
            logger.exception("Failed to queue confirmation email for %s", email)
            raise HTTPException(
                status_code=503,
                detail="Could not send activation email. Please try again later.",
            ) from exc
