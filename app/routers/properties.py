from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.deps import DB, HostUser, OptionalUser, ensure_property_owner, get_or_404
from app.models import (Amenity, Booking, CancellationPolicy, City, Photo, Property, PropertyType, Review,
                        Unit, UnitPriceCalendar, User, property_amenity)
from app.schemas import (AmenityIdsIn, PhotoIn, PhotoOut, PropertyIn, PropertyListItem, PropertyOut,
                         PropertyReviewOut, PropertyUpdate, UnitIn, UnitOut)
from app.services.booking import ACTIVE_STATUSES

router = APIRouter(tags=["اقامتگاه‌ها"])


def rating_subquery():
    return (
        select(Unit.property_id.label("pid"),
               func.round(func.avg(Review.rating), 2).label("avg_rating"),
               func.count(Review.id).label("review_count"))
        .join(Booking, Booking.unit_id == Unit.id)
        .join(Review, Review.booking_id == Booking.id)
        .group_by(Unit.property_id)
        .subquery()
    )


def rating_of(db: Session, property_id: int) -> tuple[float | None, int]:
    avg, count = db.execute(
        select(func.round(func.avg(Review.rating), 2), func.count(Review.id))
        .join(Booking, Booking.id == Review.booking_id)
        .join(Unit, Unit.id == Booking.unit_id)
        .where(Unit.property_id == property_id)
    ).one()
    return (float(avg) if avg is not None else None), count


def load_property(db: Session, property_id: int) -> Property:
    prop = db.scalar(
        select(Property).where(Property.id == property_id).options(
            selectinload(Property.units), selectinload(Property.photos), selectinload(Property.amenities),
            selectinload(Property.city), selectinload(Property.type), selectinload(Property.policy),
            selectinload(Property.host),
        ).execution_options(populate_existing=True)
    )
    if prop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"اقامتگاه با شناسه {property_id} پیدا نشد")
    return prop


def property_out(db: Session, prop: Property) -> PropertyOut:
    out = PropertyOut.model_validate(prop)
    out.avg_rating, out.review_count = rating_of(db, prop.id)
    return out


def can_manage(prop: Property, user: User | None) -> bool:
    return user is not None and (user.role == "admin" or prop.host_id == user.id)


def check_refs(db: Session, city_id=None, type_id=None, policy_id=None, amenity_ids=None) -> None:
    if city_id is not None:
        get_or_404(db, City, city_id, "شهر")
    if type_id is not None:
        get_or_404(db, PropertyType, type_id, "نوع اقامتگاه")
    if policy_id is not None:
        get_or_404(db, CancellationPolicy, policy_id, "قانون لغو")
    if amenity_ids:
        found = db.scalar(select(func.count()).select_from(Amenity).where(Amenity.id.in_(amenity_ids)))
        if found != len(set(amenity_ids)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "برخی از شناسه‌های امکانات نامعتبر است")


# ---------------------------------------------------------------- search / view
@router.get("/properties", response_model=list[PropertyListItem], summary="جستجو و فیلتر اقامتگاه‌ها")
def search_properties(
    db: DB,
    user: OptionalUser,
    q: str | None = Query(None, description="جستجو در عنوان و توضیحات"),
    city_id: int | None = None,
    city: str | None = Query(None, description="نام شهر، مثلاً: کاشان"),
    province: str | None = None,
    type_id: int | None = None,
    guests: int | None = Query(None, ge=1),
    check_in: date | None = None,
    check_out: date | None = None,
    min_price: int | None = Query(None, description="حداقل قیمت پایه هر شب (تومان)"),
    max_price: int | None = Query(None, description="حداکثر قیمت پایه هر شب (تومان)"),
    amenity_ids: Annotated[list[int] | None, Query(description="همه این امکانات را داشته باشد")] = None,
    status_filter: Literal["draft", "active", "suspended"] | None = Query(None, alias="status",
                                                                         description="فقط برای ادمین"),
    sort: Literal["newest", "price_asc", "price_desc", "rating"] = "newest",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if (check_in is None) != (check_out is None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "تاریخ ورود و خروج باید با هم ارسال شوند")
    if check_in and check_out <= check_in:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "تاریخ خروج باید بعد از تاریخ ورود باشد")

    units = (select(Unit.property_id.label("pid"),
                    func.min(Unit.base_price_per_night).label("min_price"),
                    func.max(Unit.max_guests).label("max_guests"))
             .group_by(Unit.property_id).subquery())
    rating = rating_subquery()
    cover = (select(Photo.url).where(Photo.property_id == Property.id)
             .order_by(Photo.sort_order, Photo.id).limit(1).scalar_subquery())

    stmt = (
        select(Property, City.name, City.province, PropertyType.name, units.c.min_price, units.c.max_guests,
               rating.c.avg_rating, func.coalesce(rating.c.review_count, 0), cover)
        .join(City, City.id == Property.city_id)
        .join(PropertyType, PropertyType.id == Property.type_id)
        .outerjoin(units, units.c.pid == Property.id)
        .outerjoin(rating, rating.c.pid == Property.id)
    )

    if user is not None and user.role == "admin":
        if status_filter:
            stmt = stmt.where(Property.status == status_filter)
    else:
        stmt = stmt.where(Property.status == "active")
    if q:
        stmt = stmt.where(or_(Property.title.contains(q), Property.description.contains(q)))
    if city_id:
        stmt = stmt.where(Property.city_id == city_id)
    if city:
        stmt = stmt.where(City.name == city.strip())
    if province:
        stmt = stmt.where(City.province == province.strip())
    if type_id:
        stmt = stmt.where(Property.type_id == type_id)
    if min_price is not None:
        stmt = stmt.where(units.c.min_price >= min_price)
    if max_price is not None:
        stmt = stmt.where(units.c.min_price <= max_price)
    for amenity_id in amenity_ids or []:
        stmt = stmt.where(exists().where(property_amenity.c.property_id == Property.id,
                                         property_amenity.c.amenity_id == amenity_id))

    # At least one unit must match the guest count and be free for the requested dates
    if guests or check_in:
        unit_ok = [Unit.property_id == Property.id]
        if guests:
            unit_ok.append(Unit.max_guests >= guests)
        if check_in:
            unit_ok.append(~exists().where(Booking.unit_id == Unit.id, Booking.status.in_(ACTIVE_STATUSES),
                                           Booking.check_in < check_out, Booking.check_out > check_in))
            unit_ok.append(~exists().where(UnitPriceCalendar.unit_id == Unit.id,
                                           UnitPriceCalendar.is_available.is_(False),
                                           UnitPriceCalendar.day >= check_in, UnitPriceCalendar.day < check_out))
        stmt = stmt.where(exists().where(and_(*unit_ok)))

    order = {
        "newest": [Property.id.desc()],
        "price_asc": [units.c.min_price.asc().nulls_last()],
        "price_desc": [units.c.min_price.desc().nulls_last()],
        "rating": [rating.c.avg_rating.desc().nulls_last(), Property.id],
    }[sort]
    stmt = stmt.order_by(*order).limit(limit).offset(offset)

    return [
        PropertyListItem(id=p.id, title=p.title, city=city_name, province=prov, type=type_name, status=p.status,
                         min_price_per_night=min_p, max_guests=max_g,
                         avg_rating=float(avg) if avg is not None else None, review_count=cnt, cover_photo=photo)
        for p, city_name, prov, type_name, min_p, max_g, avg, cnt, photo in db.execute(stmt).all()
    ]


@router.get("/properties/mine", response_model=list[PropertyOut], summary="اقامتگاه‌های من (میزبان)")
def my_properties(user: HostUser, db: DB):
    ids = db.scalars(select(Property.id).where(Property.host_id == user.id).order_by(Property.id)).all()
    return [property_out(db, load_property(db, pid)) for pid in ids]


@router.get("/properties/{property_id}", response_model=PropertyOut, summary="جزئیات اقامتگاه")
def get_property(property_id: int, db: DB, user: OptionalUser):
    prop = load_property(db, property_id)
    if prop.status != "active" and not can_manage(prop, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"اقامتگاه با شناسه {property_id} پیدا نشد")
    return property_out(db, prop)


@router.get("/properties/{property_id}/reviews", response_model=list[PropertyReviewOut],
            summary="نظرات مهمانان یک اقامتگاه")
def property_reviews(property_id: int, db: DB, limit: int = 20, offset: int = 0):
    get_or_404(db, Property, property_id, "اقامتگاه")
    rows = db.execute(
        select(Review, User.full_name, Unit.name)
        .join(Booking, Booking.id == Review.booking_id)
        .join(Unit, Unit.id == Booking.unit_id)
        .join(User, User.id == Booking.guest_id)
        .where(Unit.property_id == property_id)
        .order_by(Review.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return [PropertyReviewOut(id=r.id, booking_id=r.booking_id, rating=r.rating, comment=r.comment,
                              created_at=r.created_at, guest_name=name, unit_name=unit_name)
            for r, name, unit_name in rows]


# ---------------------------------------------------------------- host management
@router.post("/properties", response_model=PropertyOut, status_code=201, summary="ثبت اقامتگاه جدید (میزبان)")
def create_property(data: PropertyIn, user: HostUser, db: DB):
    check_refs(db, data.city_id, data.type_id, data.policy_id, data.amenity_ids)
    prop = Property(host_id=user.id, status="draft", **data.model_dump(exclude={"amenity_ids"}))
    if data.amenity_ids:
        prop.amenities = list(db.scalars(select(Amenity).where(Amenity.id.in_(data.amenity_ids))))
    db.add(prop)
    db.commit()
    return property_out(db, load_property(db, prop.id))


@router.patch("/properties/{property_id}", response_model=PropertyOut, summary="ویرایش اقامتگاه / تغییر وضعیت")
def update_property(property_id: int, data: PropertyUpdate, user: HostUser, db: DB):
    prop = load_property(db, property_id)
    ensure_property_owner(prop, user)
    changes = data.model_dump(exclude_unset=True)
    check_refs(db, changes.get("city_id"), changes.get("type_id"), changes.get("policy_id"))

    new_status = changes.get("status")
    if new_status and new_status != prop.status and user.role != "admin":
        if new_status == "suspended" or prop.status == "suspended":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "تعلیق یا رفع تعلیق فقط توسط پشتیبانی انجام می‌شود")
    if new_status == "active" and not prop.units:
        raise HTTPException(status.HTTP_409_CONFLICT, "برای فعال‌سازی، حداقل یک واحد تعریف کنید")

    for key, value in changes.items():
        setattr(prop, key, value)
    db.commit()
    return property_out(db, load_property(db, property_id))


@router.delete("/properties/{property_id}", status_code=204, summary="حذف اقامتگاه (فقط اگر رزروی نداشته باشد)")
def delete_property(property_id: int, user: HostUser, db: DB):
    prop = get_or_404(db, Property, property_id, "اقامتگاه")
    ensure_property_owner(prop, user)
    has_bookings = db.scalar(select(exists().where(Booking.unit_id == Unit.id, Unit.property_id == property_id)))
    if has_bookings:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "این اقامتگاه سابقه رزرو دارد و قابل حذف نیست؛ وضعیت آن را draft کنید")
    db.execute(delete(Property).where(Property.id == property_id))
    db.commit()


@router.put("/properties/{property_id}/amenities", response_model=PropertyOut, summary="تعیین امکانات اقامتگاه")
def set_amenities(property_id: int, data: AmenityIdsIn, user: HostUser, db: DB):
    prop = load_property(db, property_id)
    ensure_property_owner(prop, user)
    check_refs(db, amenity_ids=data.amenity_ids)
    prop.amenities = list(db.scalars(select(Amenity).where(Amenity.id.in_(data.amenity_ids))))
    db.commit()
    return property_out(db, load_property(db, property_id))


@router.post("/properties/{property_id}/photos", response_model=PhotoOut, status_code=201, summary="افزودن عکس")
def add_photo(property_id: int, data: PhotoIn, user: HostUser, db: DB):
    prop = get_or_404(db, Property, property_id, "اقامتگاه")
    ensure_property_owner(prop, user)
    if data.unit_id is not None:
        unit = get_or_404(db, Unit, data.unit_id, "واحد")
        if unit.property_id != property_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "این واحد متعلق به این اقامتگاه نیست")
    photo = Photo(property_id=property_id, **data.model_dump())
    db.add(photo)
    db.commit()
    return photo


@router.delete("/photos/{photo_id}", status_code=204, summary="حذف عکس")
def delete_photo(photo_id: int, user: HostUser, db: DB):
    photo = get_or_404(db, Photo, photo_id, "عکس")
    ensure_property_owner(db.get(Property, photo.property_id), user)
    db.delete(photo)
    db.commit()


@router.post("/properties/{property_id}/units", response_model=UnitOut, status_code=201,
             summary="افزودن واحد/اتاق به اقامتگاه")
def add_unit(property_id: int, data: UnitIn, user: HostUser, db: DB):
    prop = get_or_404(db, Property, property_id, "اقامتگاه")
    ensure_property_owner(prop, user)
    unit = Unit(property_id=property_id, **data.model_dump())
    db.add(unit)
    db.commit()
    return unit


@router.get("/properties/{property_id}/units", response_model=list[UnitOut], summary="واحدهای یک اقامتگاه")
def list_units(property_id: int, db: DB, user: OptionalUser):
    prop = get_or_404(db, Property, property_id, "اقامتگاه")
    if prop.status != "active" and not can_manage(prop, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"اقامتگاه با شناسه {property_id} پیدا نشد")
    return db.scalars(select(Unit).where(Unit.property_id == property_id).order_by(Unit.id)).all()
