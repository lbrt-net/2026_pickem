"""Log in on your phone: links work once, then never again; expired links never work; only a logged-in person can make one."""
from backend import phone_login
from backend.auth import upsert_user


def test_a_link_works_once(league):
    phone_login.init_schema()
    upsert_user("u-phone", "Phone Person", None, "phoneperson")
    t = phone_login.new_link("u-phone")
    user = phone_login.spend_link(t)
    assert user and user["discord_id"] == "u-phone"
    assert phone_login.spend_link(t) is None          # second tap: spent
    assert phone_login.spend_link("not-a-token") is None


def test_an_expired_link_never_works(league):
    phone_login.init_schema()
    upsert_user("u-phone2", "Phone Two", None, "phonetwo")
    t = phone_login.new_link("u-phone2")
    league.cur.execute("UPDATE login_links SET expires_at = now() - interval '1 minute' WHERE token = %s", (t,))
    league.commit()
    assert phone_login.spend_link(t) is None


def test_phone_link_flow(league):
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.auth import make_session_cookie
    from backend.config import COOKIE_NAME
    phone_login.init_schema()
    user = upsert_user("u-qr", "QR Person", None, "qrperson")
    c = TestClient(app)
    assert c.post("/auth/phone-link").status_code == 401                       # only when logged in
    r = c.post("/auth/phone-link", cookies={COOKIE_NAME: make_session_cookie(user)})
    assert r.status_code == 200
    t = r.json()["url"].split("t=")[1]
    phone = TestClient(app)
    assert "QR Person" in phone.get(f"/auth/link?t={t}").text                   # looking doesn't spend it
    first = phone.post("/auth/link", data={"t": t}, follow_redirects=False)
    assert first.status_code == 303 and COOKIE_NAME in first.headers.get("set-cookie", "")
    assert phone.post("/auth/link", data={"t": t}, follow_redirects=False).status_code == 410   # once only


def test_commissioner_link_for_a_member(league):
    """2026-10-17: the commissioner can make a one-time link for a member who can't get into Discord; nobody else can,
    and it works once."""
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.auth import make_session_cookie
    from backend.config import COOKIE_NAME
    phone_login.init_schema()
    friend = upsert_user("u-friend", "Darius Test", None, "dariustest")
    c = TestClient(app)
    assert c.post("/admin/users/u-friend/login-link", cookies={COOKIE_NAME: make_session_cookie(friend)}).status_code == 403
    r = c.post("/admin/users/u-friend/login-link?hours=6", cookies={COOKIE_NAME: make_session_cookie({"discord_id": "boss", "is_admin": True})})
    assert r.status_code == 200 and r.json()["for"] == "Darius Test" and r.json()["minutes"] == 360
    t = r.json()["url"].split("t=")[1]
    phone = TestClient(app)
    first = phone.post("/auth/link", data={"t": t}, follow_redirects=False)
    assert first.status_code == 303 and COOKIE_NAME in first.headers.get("set-cookie", "")
    assert phone.post("/auth/link", data={"t": t}, follow_redirects=False).status_code == 410
    assert c.post("/admin/users/nobody/login-link", cookies={COOKIE_NAME: make_session_cookie({"discord_id": "boss", "is_admin": True})}).status_code == 404
