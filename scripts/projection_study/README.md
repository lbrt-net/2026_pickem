# Projection study scripts

Copied from the 2026-10-06 working session. They are study scripts, not app code: they hard-code local paths
(the session scratchpad for each other, `~/PycharmProjects/nba-pipeline/data/raw/` for data) and import each other via
`runpy`. The rules they implement are written up in `PROJECTIONS.md` at the repo root.

Main entry points:
- `pipeline.py` — per-game projection for any player and target season (`project(pid, "2026-27")`).
- `run27.py` — full 2026-27 run → `projections_2026_27.csv`.
- `rookies.py` — rookie model → `rookie_projections_2026_27.csv`.
- `role_positions_single.py` — one position per player → `role_positions_single_2025_26.csv`.
- `all_players.py`, `late_check.py` — '26 validation and uncertainty.
