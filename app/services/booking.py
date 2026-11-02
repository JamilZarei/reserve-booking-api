"""Booking business logic: price calculation, availability check, coupons and refunds."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings, today
from app.models import Booking, Coupon, Unit, UnitPriceCalendar

ACTIVE_STATUSES = ("pending", "confirmed")


@dataclass
class Quote:
    unit: Unit
    check_in: date
    check_out: date
    nightly: list[tuple[date, Decimal]] = field(default_factory=list)
    coupon: Coupon | None = None

    @property
    def subtotal(self) -> Decimal:
        return sum((p for _, p in self.nightly), Decimal(0))

    @property
    def discount(self) -> Decimal:
        if not self.coupon:
            return Decimal(0)
        return (self.subtotal * self.coupon.discount_percent / 100).quantize(Decimal(1), ROUND_HALF_UP)

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount

    def as_dict(self) -> dict:
        return {
            "unit_id": self.unit.id,
            "check_in": self.check_in,
            "check_out": self.check_out,
            "nights": len(self.nightly),
            "nightly": [{"day": d, "price": p} for d, p in self.nightly],
            "subtotal": self.subtotal,
            "coupon_code": self.coupon.code if self.coupon else None,
            "discount": self.discount,
            "total_price": self.total,
        }


def conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


def validate_dates(check_in: date, check_out: date) -> None:
    if check_in < today():
        raise bad_request("تاریخ ورود نمی‌تواند در گذشته باشد")
    if check_out <= check_in:
        raise bad_request("تاریخ خروج باید بعد از تاریخ ورود باشد")
    if (check_out - check_in).days > settings.max_nights:
        raise bad_request(f"حداکثر مدت اقامت {settings.max_nights} شب است")


def coupon_remaining_uses(db: Session, coupon: Coupon) -> int:
    used = db.scalar(
        select(func.count()).select_from(Booking)
        .where(Booking.coupon_id == coupon.id, Booking.status != "cancelled")
    )
    return max(coupon.usage_limit - used, 0)


def get_valid_coupon(db: Session, code: str) -> Coupon:
    coupon = db.scalar(select(Coupon).where(func.upper(Coupon.code) == code.strip().upper()))
    if coupon is None:
        raise bad_request("کد تخفیف معتبر نیست")
    if not (coupon.valid_from <= today() <= coupon.valid_to):
        raise bad_request("مهلت استفاده از این کد تخفیف تمام شده یا هنوز شروع نشده است")
    if coupon_remaining_uses(db, coupon) <= 0:
        raise bad_request("ظرفیت استفاده از این کد تخفیف تکمیل شده است")
    return coupon


def has_overlap(db: Session, unit_id: int, check_in: date, check_out: date, exclude_id: int | None = None) -> bool:
    stmt = select(Booking.id).where(
        Booking.unit_id == unit_id,
        Booking.status.in_(ACTIVE_STATUSES),
        Booking.check_in < check_out,
        Booking.check_out > check_in,
    )
    if exclude_id:
        stmt = stmt.where(Booking.id != exclude_id)
    return db.scalar(stmt.limit(1)) is not None


def build_quote(db: Session, unit: Unit, check_in: date, check_out: date, guests: int,
                coupon_code: str | None = None) -> Quote:
    validate_dates(check_in, check_out)
    if unit.property.status != "active":
        raise conflict("این اقامتگاه در حال حاضر قابل رزرو نیست")
    if guests > unit.max_guests:
        raise bad_request(f"ظرفیت این واحد حداکثر {unit.max_guests} نفر است")

    calendar = {
        c.day: c
        for c in db.scalars(
            select(UnitPriceCalendar).where(
                UnitPriceCalendar.unit_id == unit.id,
                UnitPriceCalendar.day >= check_in,
                UnitPriceCalendar.day < check_out,
            )
        )
    }
    quote = Quote(unit=unit, check_in=check_in, check_out=check_out)
    day = check_in
    while day < check_out:
        entry = calendar.get(day)
        if entry is not None and not entry.is_available:
            raise conflict(f"واحد در تاریخ {day} توسط میزبان مسدود شده است")
        quote.nightly.append((day, entry.price if entry else unit.base_price_per_night))
        day += timedelta(days=1)

    if has_overlap(db, unit.id, check_in, check_out):
        raise conflict("این واحد در بازه انتخابی قبلاً رزرو شده است")
    if coupon_code:
        quote.coupon = get_valid_coupon(db, coupon_code)
    return quote


def refund_amount(booking: Booking, paid: Decimal, by_host: bool) -> Decimal:
    """By policy: cancelling at least free_cancel_days before check-in = full refund; otherwise refund_percent."""
    if paid <= 0:
        return Decimal(0)
    if by_host:
        return paid
    policy = booking.unit.property.policy
    days_before = (booking.check_in - today()).days
    if days_before >= policy.free_cancel_days:
        return paid
    return (paid * policy.refund_percent / 100).quantize(Decimal(1), ROUND_HALF_UP)
