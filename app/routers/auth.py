from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select

from app.deps import DB, AdminUser, CurrentUser, get_or_404
from app.models import User
from app.schemas import RegisterIn, Token, UserAdminUpdate, UserOut, UserUpdate
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["احراز هویت و کاربران"])


@router.post("/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED,
             summary="ثبت‌نام (مهمان یا میزبان)")
def register(data: RegisterIn, db: DB):
    exists = db.scalar(select(User).where(or_(User.email == data.email.lower(), User.phone == data.phone)))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "کاربری با این ایمیل یا شماره موبایل قبلاً ثبت‌نام کرده است")
    user = User(full_name=data.full_name, email=data.email.lower(), phone=data.phone,
                password_hash=hash_password(data.password), role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.post("/auth/login", response_model=Token, summary="ورود با ایمیل یا موبایل (فرم OAuth2)")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    """در فیلد `username` ایمیل یا شماره موبایل را وارد کنید."""
    username = form.username.strip().lower()
    user = db.scalar(select(User).where(or_(User.email == username, User.phone == username)))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "نام کاربری یا رمز عبور اشتباه است")
    return Token(access_token=create_access_token(user.id, user.role), user=UserOut.model_validate(user))


@router.get("/auth/me", response_model=UserOut, summary="مشخصات کاربر فعلی")
def me(user: CurrentUser):
    return user


@router.patch("/auth/me", response_model=UserOut, summary="ویرایش پروفایل")
def update_me(data: UserUpdate, user: CurrentUser, db: DB):
    if data.phone and data.phone != user.phone:
        if db.scalar(select(User).where(User.phone == data.phone)):
            raise HTTPException(status.HTTP_409_CONFLICT, "این شماره موبایل قبلاً ثبت شده است")
        user.phone = data.phone
    if data.full_name:
        user.full_name = data.full_name
    if data.password:
        user.password_hash = hash_password(data.password)
    db.commit()
    return user


@router.get("/users", response_model=list[UserOut], summary="فهرست کاربران (ادمین)")
def list_users(_: AdminUser, db: DB, response: Response, role: str | None = None, q: str | None = None,
               limit: int = Query(50, ge=1, le=200), offset: int = 0):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if q:
        q = q.strip().lower()
        stmt = stmt.where(or_(User.full_name.contains(q), User.email.contains(q), User.phone.contains(q)))
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(stmt.subquery())))
    return db.scalars(stmt.order_by(User.id).limit(limit).offset(offset)).all()


@router.get("/users/{user_id}", response_model=UserOut, summary="مشخصات یک کاربر (ادمین)")
def get_user(user_id: int, _: AdminUser, db: DB):
    return get_or_404(db, User, user_id, "کاربر")


@router.patch("/users/{user_id}", response_model=UserOut, summary="تغییر نقش / نام کاربر (ادمین)")
def admin_update_user(user_id: int, data: UserAdminUpdate, admin: AdminUser, db: DB):
    user = get_or_404(db, User, user_id, "کاربر")
    if data.role and user.id == admin.id and data.role != "admin":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "نمی‌توانید نقش ادمین را از حساب خودتان بردارید")
    if data.role:
        user.role = data.role
    if data.full_name:
        user.full_name = data.full_name
    db.commit()
    return user
