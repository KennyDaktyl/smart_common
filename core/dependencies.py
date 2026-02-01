from typing import Callable

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from smart_common.core.db import get_db
from smart_common.core.security import TokenType, decode_and_validate_token
from smart_common.enums.user import UserRole
from smart_common.models.user import User
from smart_common.repositories.user import UserRepository
from smart_common.core.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


def _validate_access_token(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict[str, str]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_and_validate_token(credentials.credentials, TokenType.ACCESS)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = _validate_access_token(credentials)
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = UserRepository(db).get_by_id(int(sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )
    return current_user


def require_role(*roles: UserRole) -> Callable[[User], User]:
    if not roles:
        raise ValueError("At least one role must be specified")

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        role_value = current_user.role
        try:
            role = (
                UserRole(role_value)
                if not isinstance(role_value, UserRole)
                else role_value
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unsupported user role",
            )

        if role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have required role",
            )

        return current_user

    return dependency


def get_current_agent(authorization: str = Header(...)):
    """
    Simple machine-to-machine auth using static token.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = authorization.removeprefix("Bearer ").strip()

    if token != settings.AGENT_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return {
        "type": "agent",
        "name": "smart_energy_agent",
    }
