"""Build the 2026-27 projections for the site's scoring rules, and load them — one command.

    python3 scripts/build_projections.py --status          # are the site's projections built for its current rules?
    python3 scripts/build_projections.py                   # rules from the site → rebuild what they change
    python3 scripts/build_projections.py --post            # … then load players + NBA teams to the site
    python3 scripts/build_projections.py --rules local     # rules from backend scoring.py (changing them here first)
    python3 scripts/build_projections.py --post --skip-build   # load what's already built
    options: --base http://localhost:8001 (default https://lbrt.net), --scenario live, --force (rebuild both sides)

The link to the site: the scoring rules are defined once (backend/fantasy_2026_27/scoring.py, or a league's own
rules) and served at GET /fantasy/2026_27/scoring. The build scores everything with those rules through the app's own
scorer (scripts/projection_study/common.py), and every load sends the rules it was built for; the site keeps them
(fantasy_proj_builds) and GET /scoring → "projections" says per side whether they still match ("stale" + what changed).
So: change the rules on the site → --status / the site shows stale → run this with --post. Change them here → edit
scoring.py, build with --rules local, deploy, then --post (the site checks them against what it actually serves).

Steps (scripts/projection_study/, rules in PROJECTIONS.md, DISPERSION.md, TEAM_SCORING.md):
  player rules changed → rookies.py → run27.py (per-game PROJ AVG) → disp2.py → disp6.py (game spread) → pmax27.py
                         (weekly curves + clutch) → availability.py (games he plays) → data/raw/projections_2026_27.csv,
                         proj_week_2026_27.json, availability_2026_27.json
  team rules changed   → team_build.py → data/raw/team_proj_week_2026_27.json, WORK/team_pool_2026_27.json
Intermediate files and the rules/manifest live in nba-pipeline data/derived/projections_2026_27/.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
STUDY = ROOT / "scripts" / "projection_study"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(ROOT / "scripts"))
import common  # noqa: E402
from common import scoring  # noqa: E402

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            k, v = _line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

SEASON = "2026-27"
MANIFEST = common.WORK / "build.json"
STEPS = {"player": ["rookies.py", "run27.py", "disp2.py", "disp6.py", "pmax27.py", "availability.py"], "team": ["team_build.py"]}


def site_rules(base: str, scenario: str) -> dict:
    r = requests.get(f"{base}/fantasy/2026_27/scoring", params={"scenario": scenario}, timeout=30)
    r.raise_for_status()
    j = r.json()
    return {"rules": scoring.validate({"player": j["player"], "team": j["team"]}), "projections": j.get("projections")}


def show_status(st: dict | None) -> None:
    if not st:
        print("site: no projection status (old server, or no league season)")
        return
    for side in ("player", "team"):
        s = st.get(side)
        if s is None:
            print(f"  {side}: no projections loaded")
        elif not s["stale"]:
            print(f"  {side}: up to date (rules {s['version']}, loaded {s['loaded_at']})")
        else:
            why = "; ".join(s["changes"]) if s["changes"] else "loaded without a rules record"
            print(f"  {side}: STALE — rules now {s['version']}, built for {s['built_for']}: {why}")


def run(step: str) -> None:
    t = time.time()
    print(f"  → {step}", flush=True)
    p = subprocess.run([sys.executable, str(STUDY / step)], cwd=ROOT, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"{step} failed:\n{p.stdout[-2000:]}\n{p.stderr[-4000:]}")
    last = [x for x in p.stdout.strip().splitlines() if x.strip()][-1:] or [""]
    print(f"    done in {time.time() - t:.0f}s  {last[0][:160]}")


def post(base: str, rules: dict) -> None:
    key = os.environ.get("INTERNAL_API_KEY", "")
    if not key:
        sys.exit("INTERNAL_API_KEY missing (.env)")
    h = {"X-Internal-Key": key}
    import load_projections
    rows = load_projections.rows()
    r = requests.post(f"{base}/fantasy/2026_27/admin/pool/load", headers=h, timeout=300,
                      json={"season": SEASON, "source": "roster", "replace": True, "rows": rows, "rules": rules})
    print("  players:", r.status_code, r.text[:300])
    teams = json.loads((common.WORK / "team_pool_2026_27.json").read_text())
    r = requests.post(f"{base}/fantasy/2026_27/admin/team-pool/load", headers=h, timeout=120,
                      json={"season": SEASON, "rows": teams, "rules": rules})
    print("  teams:", r.status_code, r.text[:300])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://lbrt.net")
    ap.add_argument("--scenario", default="live")
    ap.add_argument("--rules", choices=["site", "local"], default="site")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    site = site_rules(a.base, a.scenario)
    print(f"site {a.base} ({a.scenario}):")
    show_status(site["projections"])
    if a.status:
        return

    rules = scoring.DEFAULT if a.rules == "local" else site["rules"]
    if a.rules == "local":
        for side in ("player", "team"):
            if scoring.side_version(rules[side]) != scoring.side_version(site["rules"][side]):
                print(f"note: local {side} rules differ from the site's ({'; '.join(scoring.changes(site['rules'][side], rules[side]))})"
                      " — the site will show these projections as stale until scoring.py is deployed")
    man = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    if not a.skip_build:
        bad = common.unsupported(rules)
        if bad:
            sys.exit("the projection can't score these components yet (add the stat to the build first): " + ", ".join(bad))
        todo = [s for s in ("player", "team")
                if a.force or man.get("version", {}).get(s) != scoring.side_version(rules[s])]
        if not todo:
            print("built projections already match these rules (use --force to rebuild)")
        common.RULES_FILE.write_text(json.dumps({"player": rules["player"], "team": rules["team"]}, indent=1))
        for side in todo:
            old = man.get("rules", {}).get(side)
            print(f"building {side}" + (f" — {'; '.join(scoring.changes(old, rules[side])) or 'forced'}" if old else ""))
            for step in STEPS[side]:
                run(step)
            man.setdefault("version", {})[side] = scoring.side_version(rules[side])
            man.setdefault("rules", {})[side] = rules[side]
            man.setdefault("built_at", {})[side] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            MANIFEST.write_text(json.dumps(man, indent=1))

    if a.post:
        built = {s: man.get("rules", {}).get(s) for s in ("player", "team")}
        if not all(built.values()):
            sys.exit("nothing built yet — run without --skip-build first")
        print(f"loading to {a.base}:")
        post(a.base, built)
        show_status(site_rules(a.base, a.scenario)["projections"])


if __name__ == "__main__":
    main()
