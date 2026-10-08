# Projection study scripts

Copied from the 2026-10-06 working session. They are study scripts, not app code: they hard-code local paths
(the session scratchpad for each other, `~/PycharmProjects/nba-pipeline/data/raw/` for data) and import each other via
`runpy`. The rules they implement are written up in `PROJECTIONS.md` at the repo root.

**Building the real 2026-27 projections: `python3 scripts/build_projections.py`** (`--status`, `--post`, `--rules local`;
docstring has the details). It takes the scoring rules from the site (GET /fantasy/2026_27/scoring), scores everything
with the app's own scorer (`common.py`), reruns only the side whose rules changed (player: rookies → run27 → disp2 →
disp6 → pmax27; team: team_build), and loads players + NBA teams with the rules stamped, so the site's GET /scoring
says when projections no longer match its rules. Those build steps read/write the persistent
`nba-pipeline/data/derived/projections_2026_27/` (not the session scratchpad); the other scripts here are study-only.

Main entry points:
- `pipeline.py` — per-game projection for any player and target season (`project(pid, "2026-27")`).
- `run27.py` — full 2026-27 run → `projections_2026_27.csv`.
- `rookies.py` — rookie model → `rookie_projections_2026_27.csv`.
- `role_positions_single.py` — one position per player → `role_positions_single_2025_26.csv`.
- `all_players.py`, `late_check.py` — '26 validation and uncertainty.
