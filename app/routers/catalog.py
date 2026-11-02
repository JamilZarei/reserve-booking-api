"""Base data: cities, property types, amenities, cancellation policies."""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DB, AdminUser
from app.models import Amenity, CancellationPolicy, City, PropertyType
from app.schemas import (AmenityIn, AmenityOut, CityIn, CityOut, NameIn, PolicyIn, PolicyOut,
                         PropertyTypeOut)

router = APIRouter(tags=["اطلاعات پایه"])


def save(db: DB, obj):
    db.add(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "این مورد قبلاً ثبت شده است")
    db.refresh(obj)
    return obj


@router.get("/cities", response_model=list[CityOut], summary="فهرست شهرها")
def list_cities(db: DB, province: str | None = None, q: str | None = None):
    stmt = select(City).order_by(City.province, City.name)
    if province:
        stmt = stmt.where(City.province == province)
    if q:
        stmt = stmt.where(City.name.contains(q))
    return db.scalars(stmt).all()


@router.post("/cities", response_model=CityOut, status_code=201, summary="افزودن شهر (ادمین)")
def create_city(data: CityIn, _: AdminUser, db: DB):
    return save(db, City(**data.model_dump()))


@router.get("/property-types", response_model=list[PropertyTypeOut], summary="انواع اقامتگاه")
def list_types(db: DB):
    return db.scalars(select(PropertyType).order_by(PropertyType.id)).all()


@router.post("/property-types", response_model=PropertyTypeOut, status_code=201, summary="افزودن نوع اقامتگاه (ادمین)")
def create_type(data: NameIn, _: AdminUser, db: DB):
    return save(db, PropertyType(name=data.name))


@router.get("/amenities", response_model=list[AmenityOut], summary="امکانات")
def list_amenities(db: DB):
    return db.scalars(select(Amenity).order_by(Amenity.id)).all()


@router.post("/amenities", response_model=AmenityOut, status_code=201, summary="افزودن امکانات (ادمین)")
def create_amenity(data: AmenityIn, _: AdminUser, db: DB):
    return save(db, Amenity(**data.model_dump()))


@router.get("/cancellation-policies", response_model=list[PolicyOut], summary="قوانین لغو رزرو")
def list_policies(db: DB):
    return db.scalars(select(CancellationPolicy).order_by(CancellationPolicy.id)).all()


@router.post("/cancellation-policies", response_model=PolicyOut, status_code=201, summary="افزودن قانون لغو (ادمین)")
def create_policy(data: PolicyIn, _: AdminUser, db: DB):
    return save(db, CancellationPolicy(**data.model_dump()))
