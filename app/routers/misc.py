"""Coupons, favorites, and messages."""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.config import today
from app.deps import DB, AdminUser, CurrentUser, get_or_404
from app.models import Booking, Coupon, Favorite, Message, Property, User
from app.routers.properties import search_properties
from app.schemas import CouponCheckOut, CouponIn, CouponOut, MessageIn, MessageOut, PropertyListItem
from app.services.booking import coupon_remaining_uses

coupons = APIRouter(prefix="/coupons", tags=["کدهای تخفیف"])
favorites = APIRouter(prefix="/favorites", tags=["علاقه‌مندی‌ها"])
messages = APIRouter(prefix="/messages", tags=["پیام‌ها"])


# ------------------------------------------------------------------ coupons
@coupons.get("", response_model=list[CouponOut], summary="فهرست کدهای تخفیف (ادمین)")
def list_coupons(_: AdminUser, db: DB):
    return db.scalars(select(Coupon).order_by(Coupon.id)).all()


@coupons.post("", response_model=CouponOut, status_code=201, summary="ساخت کد تخفیف (ادمین)")
def create_coupon(data: CouponIn, _: AdminUser, db: DB):
    if data.valid_to < data.valid_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "تاریخ پایان باید بعد از تاریخ شروع باشد")
    coupon = Coupon(**data.model_dump())
    db.add(coupon)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "این کد تخفیف قبلاً ساخته شده است")
    db.refresh(coupon)
    return coupon


@coupons.get("/{code}/check", response_model=CouponCheckOut, summary="بررسی اعتبار کد تخفیف")
def check_coupon(code: str, _: CurrentUser, db: DB):
    coupon = db.scalar(select(Coupon).where(func.upper(Coupon.code) == code.strip().upper()))
    if coupon is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "کد تخفیف پیدا نشد")
    remaining = coupon_remaining_uses(db, coupon)
    valid = coupon.valid_from <= today() <= coupon.valid_to and remaining > 0
    return CouponCheckOut(code=coupon.code, discount_percent=coupon.discount_percent, valid=valid,
                          remaining_uses=remaining)


# ------------------------------------------------------------------ favorites
@favorites.get("", response_model=list[PropertyListItem], summary="اقامتگاه‌های مورد علاقه من")
def my_favorites(user: CurrentUser, db: DB):
    ids = set(db.scalars(select(Favorite.property_id).where(Favorite.user_id == user.id)))
    if not ids:
        return []
    items = search_properties(db=db, user=None, q=None, city_id=None, city=None, province=None, type_id=None,
                              guests=None, check_in=None, check_out=None, min_price=None, max_price=None,
                              amenity_ids=None, status_filter=None, sort="newest", limit=100, offset=0)
    return [i for i in items if i.id in ids]


@favorites.post("/{property_id}", status_code=201, summary="افزودن به علاقه‌مندی‌ها")
def add_favorite(property_id: int, user: CurrentUser, db: DB):
    get_or_404(db, Property, property_id, "اقامتگاه")
    if db.get(Favorite, (user.id, property_id)) is None:
        db.add(Favorite(user_id=user.id, property_id=property_id))
        db.commit()
    return {"detail": "به علاقه‌مندی‌ها اضافه شد", "property_id": property_id}


@favorites.delete("/{property_id}", status_code=204, summary="حذف از علاقه‌مندی‌ها")
def remove_favorite(property_id: int, user: CurrentUser, db: DB):
    fav = db.get(Favorite, (user.id, property_id))
    if fav is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "این اقامتگاه در علاقه‌مندی‌های شما نیست")
    db.delete(fav)
    db.commit()


# ------------------------------------------------------------------ messages
@messages.post("", response_model=MessageOut, status_code=201, summary="ارسال پیام")
def send_message(data: MessageIn, user: CurrentUser, db: DB):
    if data.receiver_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ارسال پیام به خودتان ممکن نیست")
    get_or_404(db, User, data.receiver_id, "گیرنده")
    if data.booking_id is not None:
        b = get_or_404(db, Booking, data.booking_id, "رزرو")
        parties = {b.guest_id, b.unit.property.host_id}
        if {user.id, data.receiver_id} != parties:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "پیام مربوط به رزرو فقط بین مهمان و میزبان همان رزرو است")
    msg = Message(sender_id=user.id, **data.model_dump())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@messages.get("", response_model=list[MessageOut], summary="پیام‌های من (ارسالی و دریافتی)")
def my_messages(user: CurrentUser, db: DB, with_user_id: int | None = None, booking_id: int | None = None,
                limit: int = 100, offset: int = 0):
    stmt = select(Message).where(or_(Message.sender_id == user.id, Message.receiver_id == user.id))
    if with_user_id:
        stmt = stmt.where(or_(and_(Message.sender_id == user.id, Message.receiver_id == with_user_id),
                              and_(Message.sender_id == with_user_id, Message.receiver_id == user.id)))
    if booking_id:
        stmt = stmt.where(Message.booking_id == booking_id)
    return db.scalars(stmt.order_by(Message.sent_at).limit(limit).offset(offset)).all()
