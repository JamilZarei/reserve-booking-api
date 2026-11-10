"""Admin dashboard: site-wide statistics."""
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import Date, case, cast, func, select

from app.config import settings, today
from app.deps import DB, AdminUser
from app.models import Booking, City, Payment, Property, PropertyType, Review, Unit, User
from app.routers.bookings import booking_detail
from app.schemas import AdminStats

router = APIRouter(prefix="/admin", tags=["پنل ادمین"])


def _int(value) -> int:
    return int(value or 0)


# Net amount of a payment row: paid counts positive, refunded negative, failed ignored
NET = case((Payment.status == "paid", Payment.amount), (Payment.status == "refunded", -Payment.amount), else_=0)


@router.get("/stats", response_model=AdminStats, summary="آمار کلی سایت")
def stats(_: AdminUser, db: DB, days: int = Query(180, ge=7, le=730)):
    users_by_role = dict(db.execute(select(User.role, func.count()).group_by(User.role)).all())
    props_by_status = dict(db.execute(select(Property.status, func.count()).group_by(Property.status)).all())
    bookings_by_status = dict(db.execute(select(Booking.status, func.count()).group_by(Booking.status)).all())
    revenue = db.scalar(select(func.coalesce(func.sum(NET), 0))) or Decimal(0)
    avg_rating, review_count = db.execute(select(func.avg(Review.rating), func.count(Review.id))).one()
    since = today() - timedelta(days=30)
    new_users = db.scalar(select(func.count()).select_from(User).where(cast(User.created_at, Date) >= since))

    # Daily series (Tehran time); the frontend groups it into Jalali months
    start = today() - timedelta(days=days)
    local_day = lambda col: cast(func.timezone(settings.timezone, col), Date)  # noqa: E731
    rev_rows = db.execute(
        select(local_day(Payment.paid_at).label("d"), func.sum(NET))
        .where(local_day(Payment.paid_at) >= start).group_by("d")
    ).all()
    book_rows = db.execute(
        select(local_day(Booking.created_at).label("d"), func.count())
        .where(local_day(Booking.created_at) >= start).group_by("d")
    ).all()
    series: dict = {}
    for d, amount in rev_rows:
        series.setdefault(d, {"day": d, "revenue": 0, "bookings": 0})["revenue"] = _int(amount)
    for d, count in book_rows:
        series.setdefault(d, {"day": d, "revenue": 0, "bookings": 0})["bookings"] = count

    paid_bookings = Booking.status.in_(("confirmed", "completed"))
    top_cities = db.execute(
        select(City.name, func.count(Booking.id), func.coalesce(func.sum(Booking.total_price), 0))
        .join(Property, Property.city_id == City.id).join(Unit, Unit.property_id == Property.id)
        .join(Booking, Booking.unit_id == Unit.id).where(paid_bookings)
        .group_by(City.name).order_by(func.count(Booking.id).desc()).limit(8)
    ).all()
    by_type = db.execute(
        select(PropertyType.name, func.count(Property.id))
        .join(Property, Property.type_id == PropertyType.id).where(Property.status == "active")
        .group_by(PropertyType.name).order_by(func.count(Property.id).desc())
    ).all()
    top_properties = db.execute(
        select(Property.id, Property.title, City.name, func.count(Booking.id), func.sum(Booking.total_price))
        .join(City, City.id == Property.city_id).join(Unit, Unit.property_id == Property.id)
        .join(Booking, Booking.unit_id == Unit.id).where(paid_bookings)
        .group_by(Property.id, Property.title, City.name).order_by(func.sum(Booking.total_price).desc()).limit(6)
    ).all()
    recent = db.scalars(select(Booking).order_by(Booking.created_at.desc(), Booking.id.desc()).limit(8)).all()

    return AdminStats(
        users_total=sum(users_by_role.values()), users_by_role=users_by_role, new_users_30d=new_users,
        properties_total=sum(props_by_status.values()), properties_by_status=props_by_status,
        units_total=db.scalar(select(func.count()).select_from(Unit)),
        bookings_total=sum(bookings_by_status.values()), bookings_by_status=bookings_by_status,
        revenue_total=_int(revenue),
        avg_rating=round(float(avg_rating), 2) if avg_rating is not None else None, review_count=review_count,
        daily=sorted(series.values(), key=lambda r: r["day"]),
        top_cities=[{"city": c, "bookings": n, "revenue": _int(r)} for c, n, r in top_cities],
        by_type=[{"type": t, "count": n} for t, n in by_type],
        top_properties=[{"id": i, "title": t, "city": c, "bookings": n, "revenue": _int(r)}
                        for i, t, c, n, r in top_properties],
        recent_bookings=[booking_detail(b) for b in recent],
    )
