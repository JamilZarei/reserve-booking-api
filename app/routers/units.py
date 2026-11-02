from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert

from app.deps import DB, HostUser, OptionalUser, ensure_property_owner, get_or_404
from app.models import Booking, Unit, UnitPriceCalendar
from app.schemas import CalendarDayIn, CalendarDayOut, QuoteOut, UnitOut, UnitUpdate
from app.services.booking import build_quote

router = APIRouter(prefix="/units", tags=["واحدها و تقویم قیمت"])


def visible_unit(db: DB, unit_id: int, user) -> Unit:
    unit = get_or_404(db, Unit, unit_id, "واحد")
    prop = unit.property
    if prop.status != "active" and not (user and (user.role == "admin" or user.id == prop.host_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"واحد با شناسه {unit_id} پیدا نشد")
    return unit


@router.get("/{unit_id}", response_model=UnitOut, summary="جزئیات واحد")
def get_unit(unit_id: int, db: DB, user: OptionalUser):
    return visible_unit(db, unit_id, user)


@router.patch("/{unit_id}", response_model=UnitOut, summary="ویرایش واحد (میزبان)")
def update_unit(unit_id: int, data: UnitUpdate, user: HostUser, db: DB):
    unit = get_or_404(db, Unit, unit_id, "واحد")
    ensure_property_owner(unit.property, user)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(unit, key, value)
    db.commit()
    return unit


@router.delete("/{unit_id}", status_code=204, summary="حذف واحد (فقط اگر رزروی نداشته باشد)")
def delete_unit(unit_id: int, user: HostUser, db: DB):
    unit = get_or_404(db, Unit, unit_id, "واحد")
    ensure_property_owner(unit.property, user)
    if db.scalar(select(exists().where(Booking.unit_id == unit_id))):
        raise HTTPException(status.HTTP_409_CONFLICT, "این واحد سابقه رزرو دارد و قابل حذف نیست")
    db.delete(unit)
    db.commit()


@router.get("/{unit_id}/calendar", response_model=list[CalendarDayOut],
            summary="تقویم قیمت و موجودی روزانه (روزهای رزروشده is_available=false)")
def get_calendar(unit_id: int, db: DB, user: OptionalUser,
                 start: date = Query(..., examples=["2026-11-15"]),
                 end: date = Query(..., examples=["2026-12-15"], description="انتهای بازه (بدون احتساب)")):
    unit = visible_unit(db, unit_id, user)
    if end <= start or (end - start).days > 180:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "بازه تاریخ نامعتبر است (حداکثر ۱۸۰ روز)")
    rows = {c.day: c for c in db.scalars(select(UnitPriceCalendar).where(
        UnitPriceCalendar.unit_id == unit_id, UnitPriceCalendar.day >= start, UnitPriceCalendar.day < end))}
    booked: set[date] = set()
    for b in db.scalars(select(Booking).where(Booking.unit_id == unit_id, Booking.status.in_(("pending", "confirmed")),
                                              Booking.check_in < end, Booking.check_out > start)):
        d = b.check_in
        while d < b.check_out:
            booked.add(d)
            d += timedelta(days=1)

    result, d = [], start
    while d < end:
        row = rows.get(d)
        price = row.price if row else unit.base_price_per_night
        available = (row.is_available if row else True) and d not in booked
        result.append(CalendarDayOut(day=d, price=price, is_available=available))
        d += timedelta(days=1)
    return result


@router.put("/{unit_id}/calendar", response_model=list[CalendarDayOut],
            summary="تنظیم قیمت یا مسدودسازی روزها (میزبان)")
def set_calendar(unit_id: int, days: list[CalendarDayIn], user: HostUser, db: DB):
    unit = get_or_404(db, Unit, unit_id, "واحد")
    ensure_property_owner(unit.property, user)
    if not days or len(days) > 366:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "بین ۱ تا ۳۶۶ روز ارسال کنید")
    stmt = insert(UnitPriceCalendar).values([{"unit_id": unit_id, **d.model_dump()} for d in days])
    stmt = stmt.on_conflict_do_update(
        index_elements=["unit_id", "day"],
        set_={"price": stmt.excluded.price, "is_available": stmt.excluded.is_available},
    )
    db.execute(stmt)
    db.commit()
    return days


@router.get("/{unit_id}/quote", response_model=QuoteOut, summary="استعلام قیمت و موجودی قبل از رزرو")
def quote(unit_id: int, db: DB, user: OptionalUser,
          check_in: date = Query(..., examples=["2026-11-19"]),
          check_out: date = Query(..., examples=["2026-11-22"]),
          guests: int = Query(1, ge=1),
          coupon_code: str | None = None):
    unit = visible_unit(db, unit_id, user)
    return build_quote(db, unit, check_in, check_out, guests, coupon_code).as_dict()
