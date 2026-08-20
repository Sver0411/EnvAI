from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.schemas.common import Resp
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Resp[UserOut])
def register(data: RegisterIn, db: Session = Depends(get_db)) -> Resp[UserOut]:
    user = auth_service.register(db, data)
    db.commit()
    return Resp(data=UserOut.model_validate(user))


@router.post("/login", response_model=Resp[TokenOut])
def login(data: LoginIn, db: Session = Depends(get_db)) -> Resp[TokenOut]:
    user = auth_service.authenticate(db, data)
    token = auth_service.issue_token(user)
    return Resp(data=TokenOut(access_token=token, user=UserOut.model_validate(user)))


@router.get("/me", response_model=Resp[UserOut])
def me(current_user: User = Depends(get_current_user)) -> Resp[UserOut]:
    return Resp(data=UserOut.model_validate(current_user))