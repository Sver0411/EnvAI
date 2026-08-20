import bcrypt
import jwt
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ConflictError
from app.core.security import create_access_token, decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.authorization import create_personal_organization
from app.schemas.auth import LoginIn, RegisterIn


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def register(db: Session, data: RegisterIn) -> User:
    if UserRepository.get_by_email(db, data.email) is not None:
        raise ConflictError("该邮箱已被注册")
    if UserRepository.get_by_username(db, data.username) is not None:
        raise ConflictError("该用户名已被注册")
    user = UserRepository.create(db, data, _hash_password(data.password))
    create_personal_organization(db, user)
    return user


def authenticate(db: Session, data: LoginIn) -> User:
    user = UserRepository.get_by_username(db, data.username)
    if user is None or not _verify_password(data.password, user.hashed_password) or not user.is_active or user.status != "active":
        raise AuthError("用户名或密码错误")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


def issue_token(user: User) -> str:
    return create_access_token(str(user.id))


def get_user_by_token(db: Session, token: str) -> User:
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise AuthError("无效的登录凭证")
    user_id = payload.get("sub")
    user = UserRepository.get_by_id(db, int(user_id)) if user_id else None
    if user is None or not user.is_active or user.status != "active":
        raise AuthError("用户不存在或已停用")
    return user
