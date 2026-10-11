"""Phone login links: work once, then never again; expired links never work."""
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
