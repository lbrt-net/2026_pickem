"""Resetting the draft clears its recap and Autopick switches but keeps the draft queues (DECISIONS.md, 2026-10-15 / 2026-10-17)."""
from psycopg2.extras import Json

from backend.fantasy_2026_27 import draft
from tests.integration.conftest import S

ADMIN = {"is_admin": True, "discord_id": "admin"}


def test_reset_clears_the_draft_recap(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_recaps (scenario, kind, week, data) VALUES (%s, 'draft', 0, %s) ON CONFLICT DO NOTHING",
                (S, Json({"draft": {}})))
    draft.reset(cur, S)
    cur.execute("SELECT count(*) AS n FROM fantasy_recaps WHERE scenario = %s", (S,))
    assert cur.fetchone()["n"] == 0


def test_reset_keeps_queues_clears_autopick(league):
    cur = league.cur
    cur.execute("SELECT team_order FROM fantasy_drafts WHERE scenario = %s", (S,))
    row = cur.fetchone()
    team = (row["team_order"] or ["t1"])[0] if row else "t1"
    cur.execute("INSERT INTO fantasy_draft_queue (scenario, team_id, entity_id, rank) VALUES (%s, %s, 'pa1', 0) ON CONFLICT DO NOTHING", (S, team))
    cur.execute("UPDATE fantasy_drafts SET autopick_teams = %s WHERE scenario = %s", (Json([team]), S))
    draft.reset(cur, S)
    cur.execute("SELECT count(*) AS n FROM fantasy_draft_queue WHERE scenario = %s", (S,))
    assert cur.fetchone()["n"] == 1
    cur.execute("SELECT autopick_teams FROM fantasy_drafts WHERE scenario = %s", (S,))
    assert (cur.fetchone()["autopick_teams"] or []) == []


def test_dropped_draft_pick_stays_in_the_draft(league):
    """2026-10-17: dropping a drafted player must not erase his pick (Draft Grades / results read the permanent record)."""
    cur = league.cur
    draft.start(cur, S)
    cur.execute("UPDATE fantasy_drafts SET warmup_until = NULL, clock_started_at = now() WHERE scenario = %s", (S,))
    draft.make_pick(cur, S, "pa1", ADMIN)
    cur.execute("DELETE FROM fantasy_rosters WHERE scenario = %s AND player_id = 'pa1'", (S,))   # dropped
    assert [p["player_id"] for p in draft._picks(cur, S)] == ["pa1"]


def test_draft_record_is_permanent(league):
    import psycopg2
    import pytest
    cur = league.cur
    draft.start(cur, S)
    cur.execute("UPDATE fantasy_drafts SET warmup_until = NULL, clock_started_at = now() WHERE scenario = %s", (S,))
    draft.make_pick(cur, S, "pa1", ADMIN)
    cur.execute("SAVEPOINT x")
    with pytest.raises(psycopg2.Error):
        cur.execute("DELETE FROM fantasy_draft_picks WHERE scenario = %s", (S,))   # the database refuses
    cur.execute("ROLLBACK TO SAVEPOINT x")
    draft.reset(cur, S)                                                             # a reset still may
    cur.execute("SELECT count(*) AS n FROM fantasy_draft_picks WHERE scenario = %s", (S,))
    assert cur.fetchone()["n"] == 0
