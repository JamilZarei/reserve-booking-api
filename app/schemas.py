from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Phone = Field(pattern=r"^09\d{9}$", examples=["09121112233"])


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ auth / users
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=3, max_length=120, examples=["پریسا امینی"])
    email: EmailStr
    phone: str = Phone
    password: str = Field(min_length=8, max_length=72, examples=["Pass@1234"])
    role: Literal["guest", "host"] = "guest"


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    phone: str | None = Field(default=None, pattern=r"^09\d{9}$")
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserOut(ORM):
    id: int
    full_name: str
    email: str
    phone: str
    role: str
    created_at: datetime


class UserAdminUpdate(BaseModel):
    role: Literal["guest", "host", "admin"] | None = None
    full_name: str | None = Field(default=None, min_length=3, max_length=120)


class UserBrief(ORM):
    id: int
    full_name: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ------------------------------------------------------------------ catalog
class CityIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    province: str = Field(min_length=2, max_length=80)
    country: str = "ایران"


class CityOut(ORM):
    id: int
    name: str
    province: str
    country: str


class NameIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)


class PropertyTypeOut(ORM):
    id: int
    name: str


class AmenityIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    icon: str | None = None


class AmenityOut(ORM):
    id: int
    name: str
    icon: str | None


class PolicyIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    free_cancel_days: int = Field(ge=0)
    refund_percent: float = Field(ge=0, le=100)


class PolicyOut(ORM):
    id: int
    name: str
    free_cancel_days: int
    refund_percent: float


# ------------------------------------------------------------------ units / calendar
class UnitIn(BaseModel):
    name: str = Field(min_length=2, max_length=120, examples=["اتاق دوتخته"])
    max_guests: int = Field(gt=0, le=50)
    bedrooms: int = Field(default=0, ge=0)
    beds: int = Field(default=1, ge=0)
    bathrooms: int = Field(default=1, ge=0)
    base_price_per_night: int = Field(gt=0, description="تومان", examples=[2500000])


class UnitUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    max_guests: int | None = Field(default=None, gt=0, le=50)
    bedrooms: int | None = Field(default=None, ge=0)
    beds: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    base_price_per_night: int | None = Field(default=None, gt=0)


class UnitOut(ORM):
    id: int
    property_id: int
    name: str
    max_guests: int
    bedrooms: int
    beds: int
    bathrooms: int
    base_price_per_night: int


class CalendarDayIn(BaseModel):
    day: date
    price: int = Field(gt=0)
    is_available: bool = True


class CalendarDayOut(ORM):
    day: date
    price: int
    is_available: bool


class NightPrice(BaseModel):
    day: date
    price: int


class QuoteOut(BaseModel):
    unit_id: int
    check_in: date
    check_out: date
    nights: int
    nightly: list[NightPrice]
    subtotal: int
    coupon_code: str | None = None
    discount: int = 0
    total_price: int


# ------------------------------------------------------------------ properties
class PhotoIn(BaseModel):
    url: str = Field(max_length=500, examples=["https://picsum.photos/seed/new/1024/768"])
    unit_id: int | None = None
    sort_order: int = 0


class PhotoUpdate(BaseModel):
    sort_order: int | None = None
    make_cover: bool = False


class PhotoOut(ORM):
    id: int
    unit_id: int | None
    url: str
    sort_order: int


class PropertyIn(BaseModel):
    city_id: int
    type_id: int
    policy_id: int
    title: str = Field(min_length=5, max_length=200)
    description: str | None = None
    address: str = Field(min_length=5, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    check_in_time: time = time(14, 0)
    check_out_time: time = time(12, 0)
    amenity_ids: list[int] = []
    host_id: int | None = Field(default=None, description="فقط ادمین: ثبت برای میزبان دیگر")


class PropertyUpdate(BaseModel):
    city_id: int | None = None
    type_id: int | None = None
    policy_id: int | None = None
    title: str | None = Field(default=None, min_length=5, max_length=200)
    description: str | None = None
    address: str | None = Field(default=None, min_length=5, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    check_in_time: time | None = None
    check_out_time: time | None = None
    status: Literal["draft", "active", "suspended"] | None = None


class AmenityIdsIn(BaseModel):
    amenity_ids: list[int]


class PropertyListItem(BaseModel):
    id: int
    title: str
    city: str
    province: str
    type: str
    status: str
    min_price_per_night: int | None
    max_guests: int | None
    avg_rating: float | None
    review_count: int
    cover_photo: str | None


class PropertyOut(ORM):
    id: int
    title: str
    description: str | None
    address: str
    latitude: float | None
    longitude: float | None
    check_in_time: time
    check_out_time: time
    status: str
    host: UserBrief
    city: CityOut
    type: PropertyTypeOut
    policy: PolicyOut
    units: list[UnitOut]
    photos: list[PhotoOut]
    amenities: list[AmenityOut]
    avg_rating: float | None = None
    review_count: int = 0


# ------------------------------------------------------------------ coupons
class CouponIn(BaseModel):
    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    discount_percent: float = Field(gt=0, le=100)
    valid_from: date
    valid_to: date
    usage_limit: int = Field(gt=0)


class CouponOut(ORM):
    id: int
    code: str
    discount_percent: float
    valid_from: date
    valid_to: date
    usage_limit: int


class CouponCheckOut(BaseModel):
    code: str
    discount_percent: float
    valid: bool
    remaining_uses: int


# ------------------------------------------------------------------ bookings / payments
class BookingIn(BaseModel):
    unit_id: int
    check_in: date
    check_out: date
    guests_count: int = Field(gt=0)
    coupon_code: str | None = None


class PaymentIn(BaseModel):
    method: Literal["zarinpal", "behpardakht_mellat", "sep_saman", "wallet"] = "zarinpal"
    simulate_failure: bool = Field(default=False, description="برای تست: پرداخت ناموفق شبیه‌سازی شود")


class PaymentOut(ORM):
    id: int
    booking_id: int
    amount: int
    method: str
    status: str
    transaction_ref: str | None
    paid_at: datetime


class BookingOut(ORM):
    id: int
    guest_id: int
    unit_id: int
    coupon_id: int | None
    check_in: date
    check_out: date
    guests_count: int
    total_price: int
    status: str
    created_at: datetime


class BookingDetail(BookingOut):
    guest: UserBrief
    unit: UnitOut
    property_id: int
    property_title: str
    payments: list[PaymentOut]
    review: "ReviewOut | None" = None


class CancelOut(BaseModel):
    booking: BookingOut
    refund_amount: int
    message: str


# ------------------------------------------------------------------ reviews / favorites / messages
class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewOut(ORM):
    id: int
    booking_id: int
    rating: int
    comment: str | None
    created_at: datetime


class PropertyReviewOut(ReviewOut):
    guest_name: str
    unit_name: str


class MessageIn(BaseModel):
    receiver_id: int
    booking_id: int | None = None
    body: str = Field(min_length=1, max_length=4000)


class MessageOut(ORM):
    id: int
    sender_id: int
    receiver_id: int
    booking_id: int | None
    body: str
    sent_at: datetime
    sender_name: str | None = None
    receiver_name: str | None = None


# ------------------------------------------------------------------ admin dashboard
class DailyPoint(BaseModel):
    day: date
    revenue: int
    bookings: int


class CityStat(BaseModel):
    city: str
    bookings: int
    revenue: int


class TypeStat(BaseModel):
    type: str
    count: int


class TopProperty(BaseModel):
    id: int
    title: str
    city: str
    bookings: int
    revenue: int


class AdminStats(BaseModel):
    users_total: int
    users_by_role: dict[str, int]
    new_users_30d: int
    properties_total: int
    properties_by_status: dict[str, int]
    units_total: int
    bookings_total: int
    bookings_by_status: dict[str, int]
    revenue_total: int
    avg_rating: float | None
    review_count: int
    daily: list[DailyPoint]
    top_cities: list[CityStat]
    by_type: list[TypeStat]
    top_properties: list[TopProperty]
    recent_bookings: list[BookingDetail]


BookingDetail.model_rebuild()
