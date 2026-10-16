"""Resetting the draft clears its recap, queues and Autopick switches — nothing from a test draft carries over (DECISIONS.md, 2026-10-15)."""
from psycopg2.extras import Json

from backend.fantasy_2026_27 import draft
from tests.integration.conftest import S


def test_reset_clears_the_draft_recap(league):
    cur = league.cur
    cur.execute("INSERT INTO fantasy_recaps (scenario, kind, week, data) VALUES (%s, 'draft', 0, %s) ON CONFLICT DO NOTHING",
                (S, Json({"draft": {}})))
    draft.reset(cur, S)
    cur.execute("SELECT count(*) AS n FROM fantasy_recaps WHERE scenario = %s", (S,))
    assert cur.fetchone()["n"] == 0


def test_reset_clears_queues_and_autopick(league):
    cur = league.cur
    cur.execute("SELECT team_order FROM fantasy_drafts WHERE scenario = %s", (S,))
    row = cur.fetchone()
    team = (row["team_order"] or ["t1"])[0] if row else "t1"
    cur.execute("INSERT INTO fantasy_draft_queue (scenario, team_id, entity_id, rank) VALUES (%s, %s, 'pa1', 0) ON CONFLICT DO NOTHING", (S, team))
    cur.execute("UPDATE fantasy_drafts SET autopick_teams = %s WHERE scenario = %s", (Json([team]), S))
    draft.reset(cur, S)
    cur.execute("SELECT count(*) AS n FROM fantasy_draft_queue WHERE scenario = %s", (S,))
    assert cur.fetchone()["n"] == 0
    cur.execute("SELECT autopick_teams FROM fantasy_drafts WHERE scenario = %s", (S,))
    assert (cur.fetchone()["autopick_teams"] or []) == []
