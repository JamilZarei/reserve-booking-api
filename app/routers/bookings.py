import secrets
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import today
from app.deps import DB, CurrentUser, HostUser, get_or_404
from app.models import Booking, Payment, Property, Review, Unit, User
from app.schemas import (BookingDetail, BookingIn, BookingOut, CancelOut, PaymentIn, PaymentOut, ReviewIn,
                         ReviewOut)
from app.services.booking import build_quote, refund_amount

router = APIRouter(prefix="/bookings", tags=["رزروها، پرداخت و نظر"])

BookingStatus = Literal["pending", "confirmed", "cancelled", "completed"]


def booking_detail(b: Booking) -> BookingDetail:
    return BookingDetail(
        **BookingOut.model_validate(b).model_dump(),
        guest=b.guest, unit=b.unit, property_id=b.unit.property_id,
        property_title=b.unit.property.title, payments=b.payments, review=b.review,
    )


def load_booking_for(db: Session, booking_id: int, user: User) -> Booking:
    """The guest, the property's host, and the admin can see a booking."""
    b = get_or_404(db, Booking, booking_id, "رزرو")
    if user.role != "admin" and user.id not in (b.guest_id, b.unit.property.host_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "به این رزرو دسترسی ندارید")
    return b


def paid_balance(b: Booking) -> Decimal:
    paid = sum((p.amount for p in b.payments if p.status == "paid"), Decimal(0))
    refunded = sum((p.amount for p in b.payments if p.status == "refunded"), Decimal(0))
    return paid - refunded


def new_ref(method: str) -> str:
    prefix = {"zarinpal": "ZP", "behpardakht_mellat": "BP", "sep_saman": "SEP", "wallet": "WL"}[method]
    return f"{prefix}-{secrets.randbelow(10**11):011d}"


@router.post("", response_model=BookingDetail, status_code=201, summary="ثبت رزرو (وضعیت اولیه: pending)")
def create_booking(data: BookingIn, user: CurrentUser, db: DB):
    # Lock the unit row so concurrent requests for one unit run in sequence
    unit = db.scalar(select(Unit).where(Unit.id == data.unit_id).with_for_update())
    if unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"واحد با شناسه {data.unit_id} پیدا نشد")
    if unit.property.host_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "میزبان نمی‌تواند اقامتگاه خودش را رزرو کند")

    q = build_quote(db, unit, data.check_in, data.check_out, data.guests_count, data.coupon_code)
    booking = Booking(guest_id=user.id, unit_id=unit.id, coupon_id=q.coupon.id if q.coupon else None,
                      check_in=data.check_in, check_out=data.check_out, guests_count=data.guests_count,
                      total_price=q.total, status="pending")
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:  # booking_no_overlap constraint in the database
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "این واحد در بازه انتخابی قبلاً رزرو شده است")
    db.refresh(booking)
    return booking_detail(booking)


@router.get("/me", response_model=list[BookingDetail], summary="رزروهای من (به‌عنوان مهمان)")
def my_bookings(user: CurrentUser, db: DB, status_filter: BookingStatus | None = Query(None, alias="status")):
    stmt = select(Booking).where(Booking.guest_id == user.id).order_by(Booking.check_in.desc())
    if status_filter:
        stmt = stmt.where(Booking.status == status_filter)
    return [booking_detail(b) for b in db.scalars(stmt)]


@router.get("/hosting", response_model=list[BookingDetail],
            summary="رزروهای اقامتگاه‌های من (میزبان) / همه رزروها (ادمین)")
def hosting_bookings(user: HostUser, db: DB, response: Response,
                     status_filter: BookingStatus | None = Query(None, alias="status"),
                     property_id: int | None = None, limit: int = Query(50, ge=1, le=200), offset: int = 0):
    stmt = select(Booking).join(Unit, Unit.id == Booking.unit_id).join(Property, Property.id == Unit.property_id)
    if user.role != "admin":
        stmt = stmt.where(Property.host_id == user.id)
    if status_filter:
        stmt = stmt.where(Booking.status == status_filter)
    if property_id:
        stmt = stmt.where(Property.id == property_id)
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(stmt.subquery())))
    stmt = stmt.order_by(Booking.created_at.desc(), Booking.id.desc()).limit(limit).offset(offset)
    return [booking_detail(b) for b in db.scalars(stmt)]


@router.get("/{booking_id}", response_model=BookingDetail, summary="جزئیات رزرو")
def get_booking(booking_id: int, user: CurrentUser, db: DB):
    return booking_detail(load_booking_for(db, booking_id, user))


@router.post("/{booking_id}/pay", response_model=PaymentOut, status_code=201,
             summary="پرداخت رزرو (شبیه‌سازی درگاه) — در صورت موفقیت رزرو confirmed می‌شود")
def pay_booking(booking_id: int, data: PaymentIn, user: CurrentUser, db: DB):
    b = get_or_404(db, Booking, booking_id, "رزرو")
    if b.guest_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "فقط مهمانِ همین رزرو می‌تواند پرداخت کند")
    if b.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"رزرو در وضعیت {b.status} قابل پرداخت نیست")

    payment = Payment(booking_id=b.id, amount=b.total_price, method=data.method,
                      status="failed" if data.simulate_failure else "paid", transaction_ref=new_ref(data.method))
    db.add(payment)
    if not data.simulate_failure:
        b.status = "confirmed"
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{booking_id}/payments", response_model=list[PaymentOut], summary="تراکنش‌های یک رزرو")
def booking_payments(booking_id: int, user: CurrentUser, db: DB):
    return load_booking_for(db, booking_id, user).payments


@router.post("/{booking_id}/cancel", response_model=CancelOut,
             summary="لغو رزرو و محاسبه مبلغ بازگشتی بر اساس قانون لغو")
def cancel_booking(booking_id: int, user: CurrentUser, db: DB):
    b = load_booking_for(db, booking_id, user)
    if b.status not in ("pending", "confirmed"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"رزرو در وضعیت {b.status} قابل لغو نیست")
    if b.check_in <= today():
        raise HTTPException(status.HTTP_409_CONFLICT, "پس از شروع اقامت امکان لغو آنلاین وجود ندارد")

    by_host = user.id != b.guest_id  # host or admin
    refund = refund_amount(b, paid_balance(b), by_host)
    if refund > 0:
        method = next(p.method for p in reversed(b.payments) if p.status == "paid")
        db.add(Payment(booking_id=b.id, amount=refund, method=method, status="refunded",
                       transaction_ref=new_ref(method)))
    b.status = "cancelled"
    db.commit()
    db.refresh(b)
    msg = "رزرو لغو شد." + (f" مبلغ {int(refund):,} تومان بازگشت داده می‌شود." if refund else "")
    return CancelOut(booking=b, refund_amount=refund, message=msg)


@router.post("/{booking_id}/complete", response_model=BookingOut, summary="اتمام اقامت (میزبان/ادمین)")
def complete_booking(booking_id: int, user: HostUser, db: DB):
    b = load_booking_for(db, booking_id, user)
    if b.status != "confirmed":
        raise HTTPException(status.HTTP_409_CONFLICT, "فقط رزرو تأییدشده را می‌توان تکمیل کرد")
    if b.check_out > today():
        raise HTTPException(status.HTTP_409_CONFLICT, "تاریخ خروج مهمان هنوز نرسیده است")
    b.status = "completed"
    db.commit()
    return b


@router.post("/{booking_id}/review", response_model=ReviewOut, status_code=201,
             summary="ثبت نظر (فقط مهمان و فقط پس از اتمام اقامت)")
def create_review(booking_id: int, data: ReviewIn, user: CurrentUser, db: DB):
    b = get_or_404(db, Booking, booking_id, "رزرو")
    if b.guest_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "فقط مهمانِ همین رزرو می‌تواند نظر ثبت کند")
    if b.status != "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "ثبت نظر فقط پس از اتمام اقامت ممکن است")
    if db.scalar(select(func.count()).select_from(Review).where(Review.booking_id == b.id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "برای این رزرو قبلاً نظر ثبت شده است")
    review = Review(booking_id=b.id, **data.model_dump())
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
