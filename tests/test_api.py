"""End-to-end API tests on the sample data (run in order)."""
from datetime import timedelta

from app.config import today
from tests.conftest import PASSWORD

CHECK_IN = today() + timedelta(days=30)
CHECK_OUT = CHECK_IN + timedelta(days=3)
state: dict = {}


# ------------------------------------------------------------------ health & auth
def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "database": "connected"}


def test_login_wrong_password(client):
    r = client.post("/auth/login", data={"username": "ali.mohammadi@reserve.test", "password": "wrong-pass"})
    assert r.status_code == 401


def test_register_and_duplicate(client):
    body = {"full_name": "پریسا امینی", "email": "parisa.amini@example.com", "phone": "09129876543",
            "password": PASSWORD}
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "guest"
    assert client.post("/auth/register", json=body).status_code == 409


def test_register_invalid_phone(client):
    body = {"full_name": "تست", "email": "x@reserve.test", "phone": "123", "password": PASSWORD}
    assert client.post("/auth/register", json=body).status_code == 422


def test_me_requires_token(client, guest):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=guest).json()["full_name"] == "علی محمدی"


# ------------------------------------------------------------------ catalog & search
def test_catalog(client):
    assert len(client.get("/cities").json()) == 16
    assert any(c["name"] == "کاشان" for c in client.get("/cities", params={"province": "اصفهان"}).json())
    assert len(client.get("/amenities").json()) == 20
    assert len(client.get("/cancellation-policies").json()) == 4


def test_search_by_city(client):
    items = client.get("/properties", params={"city": "کاشان"}).json()
    assert [i["id"] for i in items] == [4]
    assert items[0]["avg_rating"] == 5.0


def test_search_hides_draft_and_suspended(client):
    ids = {i["id"] for i in client.get("/properties", params={"limit": 100}).json()}
    assert 16 not in ids and 17 not in ids and len(ids) == 15


def test_search_excludes_booked_units(client):
    # Unit 1 (the property's only unit) is booked 2026-11-19..21
    params = {"city": "نوشهر", "check_in": "2026-11-19", "check_out": "2026-11-21"}
    assert client.get("/properties", params=params).json() == []
    params |= {"check_in": "2026-11-22", "check_out": "2026-11-24"}
    assert [i["id"] for i in client.get("/properties", params=params).json()] == [1]


def test_search_amenities_and_price(client):
    items = client.get("/properties", params={"amenity_ids": [3, 13], "sort": "price_asc"}).json()
    assert {i["id"] for i in items} == {1, 11}
    prices = [i["min_price_per_night"] for i in items]
    assert prices == sorted(prices)


def test_property_detail_and_reviews(client):
    p = client.get("/properties/4").json()
    assert len(p["units"]) == 3 and p["city"]["name"] == "کاشان" and p["review_count"] == 1
    assert client.get("/properties/16").status_code == 404  # draft is not public
    reviews = client.get("/properties/4/reviews").json()
    assert reviews[0]["guest_name"] == "زهرا حسینی"


# ------------------------------------------------------------------ quote & booking flow
def test_quote_with_coupon(client):
    r = client.get("/units/3/quote", params={"check_in": str(CHECK_IN), "check_out": str(CHECK_OUT),
                                             "guests": 2, "coupon_code": "welcome1405"})
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["nights"] == 3
    assert q["discount"] == round(q["subtotal"] * 0.10)
    assert q["total_price"] == q["subtotal"] - q["discount"]
    state["quote_total"] = q["total_price"]


def test_quote_errors(client):
    base = {"check_in": str(CHECK_IN), "check_out": str(CHECK_OUT)}
    assert client.get("/units/3/quote", params=base | {"guests": 9}).status_code == 400
    assert client.get("/units/3/quote", params=base | {"coupon_code": "TABESTAN1405"}).status_code == 400
    past = {"check_in": "2020-01-01", "check_out": "2020-01-03"}
    assert client.get("/units/3/quote", params=past).status_code == 400


def test_create_booking(client, guest):
    body = {"unit_id": 3, "check_in": str(CHECK_IN), "check_out": str(CHECK_OUT), "guests_count": 2,
            "coupon_code": "WELCOME1405"}
    r = client.post("/bookings", json=body, headers=guest)
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["status"] == "pending" and b["total_price"] == state["quote_total"]
    assert b["property_title"].startswith("سوئیت‌های ساحلی رامسر")
    state["booking_id"] = b["id"]


def test_overlapping_booking_rejected(client, guest2):
    body = {"unit_id": 3, "check_in": str(CHECK_IN + timedelta(days=1)),
            "check_out": str(CHECK_OUT + timedelta(days=1)), "guests_count": 1}
    assert client.post("/bookings", json=body, headers=guest2).status_code == 409


def test_host_cannot_book_own_property(client, host):
    body = {"unit_id": 4, "check_in": str(CHECK_IN), "check_out": str(CHECK_OUT), "guests_count": 1}
    assert client.post("/bookings", json=body, headers=host).status_code == 400


def test_booking_access_control(client, guest, guest2, host):
    bid = state["booking_id"]
    assert client.get(f"/bookings/{bid}", headers=guest).status_code == 200
    assert client.get(f"/bookings/{bid}", headers=host).status_code == 200
    assert client.get(f"/bookings/{bid}", headers=guest2).status_code == 403
    hosting = client.get("/bookings/hosting", headers=host).json()
    assert bid in [b["id"] for b in hosting]
    assert client.get("/bookings/hosting", headers=guest).status_code == 403


def test_failed_then_successful_payment(client, guest):
    bid = state["booking_id"]
    r = client.post(f"/bookings/{bid}/pay", json={"method": "sep_saman", "simulate_failure": True}, headers=guest)
    assert r.json()["status"] == "failed"
    assert client.get(f"/bookings/{bid}", headers=guest).json()["status"] == "pending"

    r = client.post(f"/bookings/{bid}/pay", json={"method": "zarinpal"}, headers=guest)
    assert r.status_code == 201 and r.json()["status"] == "paid"
    assert r.json()["transaction_ref"].startswith("ZP-")
    assert client.get(f"/bookings/{bid}", headers=guest).json()["status"] == "confirmed"
    assert client.post(f"/bookings/{bid}/pay", json={}, headers=guest).status_code == 409


def test_cancel_with_full_refund(client, guest):
    bid = state["booking_id"]
    r = client.post(f"/bookings/{bid}/cancel", headers=guest)
    assert r.status_code == 200, r.text
    assert r.json()["refund_amount"] == state["quote_total"]  # ۳۰ روز قبل → قانون سهل‌گیرانه → کامل
    statuses = [p["status"] for p in client.get(f"/bookings/{bid}/payments", headers=guest).json()]
    assert statuses == ["failed", "paid", "refunded"]
    assert client.post(f"/bookings/{bid}/cancel", headers=guest).status_code == 409


def test_unit_free_again_after_cancel(client, guest2):
    body = {"unit_id": 3, "check_in": str(CHECK_IN), "check_out": str(CHECK_OUT), "guests_count": 2}
    assert client.post("/bookings", json=body, headers=guest2).status_code == 201


def test_my_bookings(client, guest):
    mine = client.get("/bookings/me", headers=guest).json()
    assert {b["id"] for b in mine} >= {1, 7, state["booking_id"]}
    completed = client.get("/bookings/me", params={"status": "completed"}, headers=guest).json()
    assert [b["id"] for b in completed] == [1]


# ------------------------------------------------------------------ reviews
def test_review_rules(client, guest, guest2):
    assert client.post("/bookings/1/review", json={"rating": 4}, headers=guest).status_code == 409  # already has one
    assert client.post("/bookings/9/review", json={"rating": 4}, headers=guest2).status_code == 409  # not completed
    assert client.post("/bookings/8/review", json={"rating": 4}, headers=guest).status_code == 403  # not their booking


def test_review_created(client):
    from tests.conftest import login
    saeed = login(client, "saeed.nouri@reserve.test")
    r = client.post("/bookings/8/review", json={"rating": 5, "comment": "ویلا عالی بود"}, headers=saeed)
    assert r.status_code == 201
    assert client.get("/properties/2").json()["review_count"] == 1


# ------------------------------------------------------------------ host management
def test_host_creates_property_flow(client, host, guest):
    body = {"city_id": 2, "type_id": 2, "policy_id": 2, "title": "سوئیت جدید تست در رامسر",
            "address": "مازندران، رامسر، خیابان ساحلی", "amenity_ids": [1, 2, 13]}
    r = client.post("/properties", json=body, headers=host)
    assert r.status_code == 201 and r.json()["status"] == "draft"
    pid = r.json()["id"]
    assert client.post("/properties", json=body, headers=guest).status_code == 403

    assert client.patch(f"/properties/{pid}", json={"status": "active"}, headers=host).status_code == 409
    unit = client.post(f"/properties/{pid}/units", json={"name": "سوئیت", "max_guests": 2,
                                                          "base_price_per_night": 2000000}, headers=host).json()
    assert client.patch(f"/properties/{pid}", json={"status": "active"}, headers=host).json()["status"] == "active"
    assert client.patch(f"/properties/{pid}", json={"status": "suspended"}, headers=host).status_code == 403

    day = str(CHECK_IN)
    r = client.put(f"/units/{unit['id']}/calendar", headers=host,
                   json=[{"day": day, "price": 2500000, "is_available": False}])
    assert r.status_code == 200
    cal = client.get(f"/units/{unit['id']}/calendar", params={"start": day, "end": str(CHECK_OUT)}).json()
    assert cal[0] == {"day": day, "price": 2500000, "is_available": False}
    q = client.get(f"/units/{unit['id']}/quote", params={"check_in": day, "check_out": str(CHECK_OUT)})
    assert q.status_code == 409

    assert client.post(f"/properties/{pid}/photos", json={"url": "https://picsum.photos/seed/x/800/600"},
                       headers=host).status_code == 201
    assert client.delete(f"/properties/{pid}", headers=host).status_code == 204


def test_host_cannot_edit_others_property(client, host):
    assert client.patch("/properties/4", json={"title": "تغییر غیرمجاز عنوان"}, headers=host).status_code == 403


def test_property_with_bookings_cannot_be_deleted(client, host):
    assert client.delete("/properties/1", headers=host).status_code == 409


# ------------------------------------------------------------------ favorites / messages / admin
def test_favorites(client, guest):
    assert {f["id"] for f in client.get("/favorites", headers=guest).json()} == {2, 11}
    assert client.post("/favorites/4", headers=guest).status_code == 201
    assert client.delete("/favorites/4", headers=guest).status_code == 204
    assert client.delete("/favorites/4", headers=guest).status_code == 404


def test_messages(client, guest2, host, guest):
    thread = client.get("/messages", params={"booking_id": 9}, headers=guest2).json()
    assert len(thread) == 4
    r = client.post("/messages", json={"receiver_id": 2, "booking_id": 9, "body": "ممنون، می‌بینمتون"}, headers=guest2)
    assert r.status_code == 201
    r = client.post("/messages", json={"receiver_id": 2, "booking_id": 9, "body": "سلام"}, headers=guest)
    assert r.status_code == 403
    assert len(client.get("/messages", params={"with_user_id": 9}, headers=host).json()) == 5


def test_admin_endpoints(client, admin, guest):
    assert len(client.get("/users", params={"role": "host"}, headers=admin).json()) == 6
    assert client.get("/users", headers=guest).status_code == 403
    r = client.post("/coupons", headers=admin, json={"code": "TEST20", "discount_percent": 20,
                                                     "valid_from": str(today()), "valid_to": str(CHECK_OUT),
                                                     "usage_limit": 1})
    assert r.status_code == 201
    assert client.get("/coupons/TEST20/check", headers=guest).json()["valid"] is True
    drafts = client.get("/properties", params={"status": "draft"}, headers=admin).json()
    assert [p["id"] for p in drafts] == [16]
