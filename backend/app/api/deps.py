from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ForbiddenError
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import get_user_by_token
from app.services.authorization import current_organization
from app.models.tenant import Organization

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AuthError("未提供登录凭证")
    return get_user_by_token(db, credentials.credentials)


def require_platform_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Platform console guard; organization membership is never sufficient."""
    if current_user.platform_role not in {"platform_admin", "platform_super_admin"}:
        raise ForbiddenError("需要平台管理员权限")
    return current_user


def require_platform_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.platform_role != "platform_super_admin":
        raise ForbiddenError("需要平台超级管理员权限")
    return current_user


def get_current_organization(
    current_user: User = Depends(get_current_user),
    organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
    db: Session = Depends(get_db),
) -> Organization:
    parsed = int(organization_id) if organization_id and organization_id.isdigit() else None
    return current_organization(db, current_user, parsed)
