from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Property, User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(db: DB, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="ابتدا وارد حساب کاربری شوید (توکن نامعتبر یا منقضی است)",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise unauthorized
    user_id = decode_access_token(token)
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise unauthorized
    return user


def get_optional_user(db: DB, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User | None:
    user_id = decode_access_token(token) if token else None
    return db.get(User, user_id) if user_id else None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_roles(*roles: str):
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "شما دسترسی لازم برای این عملیات را ندارید")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles("admin"))]
HostUser = Annotated[User, Depends(require_roles("host", "admin"))]


def get_or_404(db: Session, model, obj_id: int, label: str = "مورد"):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} با شناسه {obj_id} پیدا نشد")
    return obj


def ensure_property_owner(prop: Property, user: User) -> None:
    if user.role != "admin" and prop.host_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "این اقامتگاه متعلق به شما نیست")
