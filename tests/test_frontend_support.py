"""Endpoints added for the Next.js frontend: admin stats, photo upload, pagination totals, role changes."""
import io

from conftest import login


def test_properties_total_header_and_city_search(client):
    r = client.get("/properties", params={"limit": 5})
    assert r.status_code == 200
    assert int(r.headers["x-total-count"]) == 15 and len(r.json()) == 5
    # q also matches the city name
    assert {i["city"] for i in client.get("/properties", params={"q": "کاشان"}).json()} == {"کاشان"}


def test_admin_stats(client, admin, guest):
    assert client.get("/admin/stats", headers=guest).status_code == 403
    s = client.get("/admin/stats", headers=admin).json()
    assert s["properties_total"] == 17 and s["users_total"] >= 15
    assert s["bookings_by_status"]["completed"] >= 1 and s["revenue_total"] > 0
    assert s["top_cities"] and s["recent_bookings"]


def test_admin_changes_role_and_lists_with_total(client, admin):
    r = client.get("/users", params={"q": "zahra", "limit": 5}, headers=admin)
    assert r.headers["x-total-count"] == "1"
    uid = r.json()[0]["id"]
    assert client.patch(f"/users/{uid}", json={"role": "host"}, headers=admin).json()["role"] == "host"
    assert client.patch(f"/users/{uid}", json={"role": "guest"}, headers=admin).json()["role"] == "guest"
    me = client.get("/auth/me", headers=admin).json()
    assert client.patch(f"/users/{me['id']}", json={"role": "guest"}, headers=admin).status_code == 400


def test_admin_creates_property_for_host_and_uploads_photo(client, admin, host):
    body = {"city_id": 9, "type_id": 9, "policy_id": 2, "title": "هتل سنتی تست آپلود", "address": "یزد، محله فهادان",
            "host_id": 4}
    r = client.post("/properties", json=body, headers=admin)
    assert r.status_code == 201 and r.json()["host"]["id"] == 4
    pid = r.json()["id"]
    # a host can't assign another host
    assert client.post("/properties", json=body, headers=host).status_code == 403

    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 100
    files = [("files", ("a.jpg", io.BytesIO(jpeg), "image/jpeg")), ("files", ("b.jpg", io.BytesIO(jpeg), "image/jpeg"))]
    up = client.post(f"/properties/{pid}/photos/upload", files=files, headers=admin)
    assert up.status_code == 201 and len(up.json()) == 2
    photo_url = up.json()[1]["url"]
    assert photo_url.startswith(f"/uploads/properties/{pid}/") and client.get(photo_url).status_code == 200

    bad = client.post(f"/properties/{pid}/photos/upload", headers=admin,
                      files=[("files", ("x.gif", io.BytesIO(b"GIF89a"), "image/gif"))])
    assert bad.status_code == 415

    second = up.json()[1]["id"]
    assert client.patch(f"/photos/{second}", json={"make_cover": True}, headers=admin).status_code == 200
    assert client.get(f"/properties/{pid}", headers=admin).json()["photos"][0]["id"] == second
    assert client.delete(f"/photos/{second}", headers=admin).status_code == 204
    assert client.get(photo_url).status_code == 404  # file removed from disk
    assert client.delete(f"/properties/{pid}", headers=admin).status_code == 204


def test_booking_detail_includes_review_and_messages_have_names(client):
    saeed = login(client, "saeed.nouri@reserve.test")
    ali = login(client, "ali.mohammadi@reserve.test")
    b1 = client.get("/bookings/1", headers=ali).json()
    assert b1["review"]["rating"] == 5
    msgs = client.get("/messages", headers=login(client, "zahra.hosseini@reserve.test")).json()
    assert msgs and msgs[0]["sender_name"] and msgs[0]["receiver_name"]
    assert client.get("/bookings/me", headers=saeed).status_code == 200


def test_favorites_are_not_limited_to_newest_properties(client):
    ali = login(client, "ali.mohammadi@reserve.test")
    ids = {f["id"] for f in client.get("/favorites", headers=ali).json()}
    assert {2, 11} <= ids
