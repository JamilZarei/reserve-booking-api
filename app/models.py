"""SQLAlchemy models; mirror db/schema.sql exactly (the tables are created by schema.sql)."""
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Numeric, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

Money = Numeric(14, 0)

property_amenity = Table(
    "property_amenity",
    Base.metadata,
    Column("property_id", ForeignKey("property.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenity.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True)
    phone: Mapped[str] = mapped_column(String(11), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="guest")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class City(Base):
    __tablename__ = "city"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    province: Mapped[str] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(80), default="ایران")


class PropertyType(Base):
    __tablename__ = "property_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class CancellationPolicy(Base):
    __tablename__ = "cancellation_policy"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    free_cancel_days: Mapped[int]
    refund_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))


class Amenity(Base):
    __tablename__ = "amenity"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    icon: Mapped[str | None] = mapped_column(String(60))


class Property(Base):
    __tablename__ = "property"

    id: Mapped[int] = mapped_column(primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"))
    city_id: Mapped[int] = mapped_column(ForeignKey("city.id"))
    type_id: Mapped[int] = mapped_column(ForeignKey("property_type.id"))
    policy_id: Mapped[int] = mapped_column(ForeignKey("cancellation_policy.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(300))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    check_in_time: Mapped[time] = mapped_column(default=time(14, 0))
    check_out_time: Mapped[time] = mapped_column(default=time(12, 0))
    status: Mapped[str] = mapped_column(String(10), default="draft")

    host: Mapped[User] = relationship()
    city: Mapped[City] = relationship()
    type: Mapped[PropertyType] = relationship()
    policy: Mapped[CancellationPolicy] = relationship()
    units: Mapped[list["Unit"]] = relationship(back_populates="property", order_by="Unit.id")
    photos: Mapped[list["Photo"]] = relationship(order_by="Photo.sort_order", cascade="all, delete-orphan")
    amenities: Mapped[list[Amenity]] = relationship(secondary=property_amenity, order_by="Amenity.id")


class Unit(Base):
    __tablename__ = "unit"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("property.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    max_guests: Mapped[int]
    bedrooms: Mapped[int] = mapped_column(default=0)
    beds: Mapped[int] = mapped_column(default=1)
    bathrooms: Mapped[int] = mapped_column(default=1)
    base_price_per_night: Mapped[Decimal] = mapped_column(Money)

    property: Mapped[Property] = relationship(back_populates="units")


class UnitPriceCalendar(Base):
    __tablename__ = "unit_price_calendar"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id", ondelete="CASCADE"))
    day: Mapped[date]
    price: Mapped[Decimal] = mapped_column(Money)
    is_available: Mapped[bool] = mapped_column(default=True)


class Photo(Base):
    __tablename__ = "photo"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("property.id", ondelete="CASCADE"))
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("unit.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(default=0)


class Coupon(Base):
    __tablename__ = "coupon"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    valid_from: Mapped[date]
    valid_to: Mapped[date]
    usage_limit: Mapped[int]


class Booking(Base):
    __tablename__ = "booking"

    id: Mapped[int] = mapped_column(primary_key=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("unit.id"))
    coupon_id: Mapped[int | None] = mapped_column(ForeignKey("coupon.id", ondelete="SET NULL"))
    check_in: Mapped[date]
    check_out: Mapped[date]
    guests_count: Mapped[int]
    total_price: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    guest: Mapped[User] = relationship()
    unit: Mapped[Unit] = relationship()
    coupon: Mapped[Coupon | None] = relationship()
    payments: Mapped[list["Payment"]] = relationship(order_by="Payment.id")
    review: Mapped["Review | None"] = relationship(back_populates="booking")


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"))
    amount: Mapped[Decimal] = mapped_column(Money)
    method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(10))
    transaction_ref: Mapped[str | None] = mapped_column(String(64), unique=True)
    paid_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Review(Base):
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("booking.id", ondelete="CASCADE"), unique=True)
    rating: Mapped[int]
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    booking: Mapped[Booking] = relationship(back_populates="review")


class Favorite(Base):
    __tablename__ = "favorite"

    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("property.id", ondelete="CASCADE"), primary_key=True)


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    receiver_id: Mapped[int] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("booking.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(server_default=func.now())
