# DATA.md — one truth per fact

Written 2026-10-18 after draft night, when the same player showed different positions, NBA teams, owners and draft
records on different pages. Page *design* may differ between pages; **facts may not**. Every fact below has exactly
one source; every page reads it (or a mirror that is kept equal to it automatically), and a check proves they agree.

| Fact | Source of truth | Mirrors kept equal | How it stays equal | Checked by |
|---|---|---|---|---|
| Player position (G / F / C) | season pool `fantasy_pool.position` (role-based; league vote 2026-10-17) | `fantasy_players.position` (rosters, seating, lineups, transaction log, trades read it) | `truth.sync` at startup, after every pool load / rebuild / new-player add, nightly | `test_one_truth.py`, `test_position_sync.py`, `data_audit.py` |
| Player NBA team | `fantasy_pool.nba_team`, moved to the team of his latest regular-season game (real trades) | `fantasy_players.nba_team` | same `truth.sync` | same |
| PROJ MAX / AVG / GP shown anywhere | `projections.shown_max` over `fantasy_pool.proj_weeks` (the draft list's number) | — (board, player page, pop-up, Draft Grades, roster bars all call it) | one function | `data_audit.py` (board vs player page vs Draft Grades) |
| This week's projection (Roster / Matchup) | the projection model's curve × games left × availability, blended into the season's games (+25% a week) | — | `lineup.week_view` only | — (a different, labelled number: it's the week, not the season) |
| Win chance | the server's simulation (`winprob`) | — (pages never estimate it themselves) | one endpoint | — |
| Who owns a player / NBA team | `fantasy_rosters` (live roster) | weekly lineups (`etch`) are frozen history by design | — | `data_audit.py` (`/players`, `/teams`, week views, player page) |
| Roster spot | `fantasy_rosters.slot` | — | moves / checkout / trades / draft seating write it | `data_audit.py` (spot fits position, no spot over its limit, nobody on two teams) |
| The draft (who, which team, price, spot) | `fantasy_draft_picks` — permanent; the database refuses changes except the draft itself, a reset, and the commissioner repair tool | Draft Grades (`fantasy_recaps`, rebuilt from it) | `draft._picks` reads only the record | `test_draft_reset_recap.py`, `data_audit.py` (record vs Draft Grades vs player pages) |
| Fantasy team name / abbreviation / color / owner | `fantasy_teams` | — | — | `data_audit.py` (`/league/members` vs `/teams`, draft order, trades, transaction log) |
| Transactions (adds / drops / claims / trades) | `fantasy_transactions` | — | — | — |
| Box scores / stats | `nba_player_games` (nightly job, NIGHTLY.md) | `fantasy_players` season averages (last season's, for the Players list) | rebuilt from box scores | — |

## The checks
- **On every push (CI):** `tests/integration/test_one_truth.py` starts with the two position/team tables disagreeing and
  proves every view shows the pool's values after the sync, and that a real trade moves the player everywhere.
- **After every deploy:** `python3 scripts/check_site.py` runs `scripts/data_audit.py`, which reads the live site like a
  visitor and compares every fact above across every page that shows it. Any disagreement fails the check.
- **Any time:** `python3 scripts/data_audit.py` (add `--quick` to skip the per-player pages).

## Rules
1. A new page or endpoint that shows one of these facts reads the source (or its kept-equal mirror) — never a copy of
   its own. If it needs a new mirror, the mirror goes in this table with how it's kept equal and a check.
2. Never write `fantasy_players.position` / `nba_team` directly; change the pool and let `truth.sync` copy it.
3. Finished things are locked: the draft record, frozen weekly lineups, frozen recaps.
