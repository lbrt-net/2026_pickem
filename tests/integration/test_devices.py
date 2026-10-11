"""Logged-in devices: every login is listed (device, how, last active); logging one out really logs it out."""
from fastapi.testclient import TestClient

from backend import auth, phone_login
from backend.auth import make_session_cookie, upsert_user
from backend.config import COOKIE_NAME
from backend.main import app

IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1"
MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"


def login_by_phone(user):
    t = phone_login.new_link(user["discord_id"])
    phone = TestClient(app, headers={"user-agent": IPHONE})
    r = phone.post("/auth/link", data={"t": t}, follow_redirects=False)
    phone.cookies.set(COOKIE_NAME, r.cookies.get(COOKIE_NAME))
    return phone


def test_list_and_log_out_a_device(league):
    phone_login.init_schema()
    user = upsert_user("u-dev", "Device Person", None, "deviceperson")
    phone = login_by_phone(user)
    computer = login_by_phone(user)                    # a second login ("computer")
    computer.headers["user-agent"] = MAC
    listed = computer.get("/auth/sessions").json()
    assert len(listed) == 2 and all(d["device"] == "iPhone · Safari" and d["method"] == "phone" for d in listed)
    assert sum(d["current"] for d in listed) == 1
    other = next(d for d in listed if not d["current"])
    left = computer.post(f"/auth/sessions/{other['id']}/end").json()
    assert len(left) == 1 and left[0]["current"]
    auth._SID_CACHE.clear()
    assert phone.get("/me").json() in (None, {}) or phone.get("/me").status_code == 401   # the phone is logged out


def test_log_out_everywhere_else_keeps_this_one(league):
    phone_login.init_schema()
    user = upsert_user("u-dev2", "Device Two", None, "devicetwo")
    a, b, c = login_by_phone(user), login_by_phone(user), login_by_phone(user)
    assert len(c.post("/auth/sessions/end-others").json()) == 1
    auth._SID_CACHE.clear()
    assert c.get("/auth/sessions").status_code == 200 and a.get("/auth/sessions").status_code == 401


def test_old_cookies_without_a_device_record_still_work(league):
    user = upsert_user("u-dev3", "Old Cookie", None, "oldcookie")
    old = TestClient(app, cookies={COOKIE_NAME: make_session_cookie(user)})
    assert old.get("/auth/sessions").status_code == 200


def test_device_names():
    assert auth.device_label(IPHONE) == "iPhone · Safari"
    assert auth.device_label(MAC) == "Mac · Chrome"
    assert auth.device_label("") == "Device · Browser"
