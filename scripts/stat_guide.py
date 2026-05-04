"""
stat_guide.py — Fetch per-game stat leader data for pick'em and POST to backend.

Hardcoded: which teams and stats to pull (update SERIES each round).
Everything else comes from the NBA API at runtime.

Column keys: rs, post, r1, r2, cf  (null if that round hasn't happened yet)

Usage:
    python3 scripts/stat_guide.py                             # print JSON
    python3 scripts/stat_guide.py --out stat_guide_semis.md   # also save markdown
    python3 scripts/stat_guide.py --post --cookie "session=..." [--base-url http://...]
"""

import argparse
import json
import os
import time
from pathlib import Path

import requests
import pandas as pd

# Load .env from project root
_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            k, v = _line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
from nba_api.stats.endpoints import (
    LeagueDashPlayerStats,
    LeagueHustleStatsPlayer,
    LeagueDashPlayerPtShot,
)

SEASON   = "2025-26"
BASE_URL = "https://pickem.lbrt.net"

ROUND_KEY = {1: "r1", 2: "r2", 3: "cf"}

# ── Series config — update each round ─────────────────────────────────────────
# teams:    full names matching team_a/team_b in the DB
# abbrs:    NBA API team abbreviations (same order as teams)
# po_rounds: playoff rounds to include as columns [1], [1,2], [1,2,3]
# per_team: True → top_n per team instead of overall

SERIES = [
    # ── Conf Semis ────────────────────────────────────────────────────────────
    {
        "teams":     ["Oklahoma City", "LA Lakers"],
        "abbrs":     ["OKC", "LAL"],
        "stat":      "Pts in Paint / game",
        "fetch":     "misc",
        "col":       "PTS_PAINT",
        "top_n":     10,
        "po_rounds": [1],
    },
    {
        "teams":     ["Minnesota", "San Antonio"],
        "abbrs":     ["MIN", "SAS"],
        "stat":      "Open/Wide Open 3PM / game",
        "fetch":     "open3",
        "col":       "FG3M",
        "top_n":     10,
        "po_rounds": [1],
    },
    {
        "teams":     ["Detroit", "Cleveland", "Toronto"],
        "abbrs":     ["DET", "CLE", "TOR"],
        "stat":      "Turnovers / game",
        "fetch":     "trad",
        "col":       "TOV",
        "top_n":     5,
        "per_team":  True,
        "po_rounds": [1],
    },
    {
        "teams":     ["New York", "Philadelphia"],
        "abbrs":     ["NYK", "PHI"],
        "stat":      "Contested 3PT Att / game",
        "fetch":     "hustle",
        "col":       "CONTESTED_SHOTS_3PT",
        "top_n":     10,
        "po_rounds": [1],
    },

    # ── Conf Finals (placeholder — update stats/teams once semis are done) ───
    {
        "teams":     ["Oklahoma City", "LA Lakers", "Minnesota", "San Antonio"],
        "abbrs":     ["OKC", "LAL", "MIN", "SAS"],
        "stat":      "Points / game",
        "fetch":     "trad",
        "col":       "PTS",
        "top_n":     10,
        "po_rounds": [1, 2],
    },
    {
        "teams":     ["Detroit", "Cleveland", "Toronto", "New York", "Philadelphia"],
        "abbrs":     ["DET", "CLE", "TOR", "NYK", "PHI"],
        "stat":      "Points / game",
        "fetch":     "trad",
        "col":       "PTS",
        "top_n":     5,
        "per_team":  True,
        "po_rounds": [1, 2],
    },

    # ── Finals (placeholder — update once CF teams are known) ─────────────────
    {
        "teams":     ["Oklahoma City", "LA Lakers", "Minnesota", "San Antonio",
                      "Detroit", "Cleveland", "Toronto", "New York", "Philadelphia"],
        "abbrs":     ["OKC", "LAL", "MIN", "SAS", "DET", "CLE", "TOR", "NYK", "PHI"],
        "stat":      "Points / game",
        "fetch":     "trad",
        "col":       "PTS",
        "top_n":     10,
        "po_rounds": [1, 2, 3],
    },
]

ASB_DATE = "02/16/2026"


def sleep():
    time.sleep(0.7)


# ── Fetchers ──────────────────────────────────────────────────────────────────

def fetch_misc(season_type, po_round=None, season_segment=None):
    kw = {}
    if po_round:       kw["po_round_nullable"]      = po_round
    if season_segment: kw["season_segment_nullable"] = season_segment
    r = LeagueDashPlayerStats(
        measure_type_detailed_defense="Misc",
        per_mode_detailed="PerGame",
        season=SEASON, season_type_all_star=season_type,
        timeout=60, **kw,
    )
    sleep()
    return r.get_data_frames()[0]


def fetch_trad(season_type, po_round=None, season_segment=None):
    kw = {}
    if po_round:       kw["po_round_nullable"]      = po_round
    if season_segment: kw["season_segment_nullable"] = season_segment
    r = LeagueDashPlayerStats(
        measure_type_detailed_defense="Base",
        per_mode_detailed="PerGame",
        season=SEASON, season_type_all_star=season_type,
        timeout=60, **kw,
    )
    sleep()
    return r.get_data_frames()[0]


def fetch_hustle(season_type, po_round=None, season_segment=None):
    kw = {}
    if po_round:       kw["po_round_nullable"] = po_round
    if season_segment: kw["date_from_nullable"] = ASB_DATE
    for attempt in range(3):
        try:
            r = LeagueHustleStatsPlayer(
                per_mode_time="PerGame",
                season=SEASON, season_type_all_star=season_type,
                timeout=60, **kw,
            )
            sleep()
            return r.get_data_frames()[0]
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  retry {attempt+1}: {e}", flush=True)
            time.sleep(3)


def fetch_open3(season_type, po_round=None, season_segment=None):
    kw = {}
    if po_round:       kw["po_round_nullable"]      = po_round
    if season_segment: kw["season_segment_nullable"] = season_segment
    dfs = []
    for dist in ["4-6 Feet - Open", "6+ Feet - Wide Open"]:
        r = LeagueDashPlayerPtShot(
            per_mode_simple="PerGame",
            season=SEASON, season_type_all_star=season_type,
            close_def_dist_range_nullable=dist,
            shot_dist_range_nullable=">=10.0",
            period_nullable=0, timeout=60, **kw,
        )
        df = r.get_data_frames()[0][["PLAYER_ID", "PLAYER_NAME", "PLAYER_LAST_TEAM_ABBREVIATION", "FG3M", "FG3A"]]
        df = df.rename(columns={"PLAYER_LAST_TEAM_ABBREVIATION": "TEAM_ABBREVIATION"})
        dfs.append(df)
        sleep()
    return pd.concat(dfs).groupby(
        ["PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION"], as_index=False
    )[["FG3M", "FG3A"]].sum()


FETCHERS = {"misc": fetch_misc, "trad": fetch_trad, "hustle": fetch_hustle, "open3": fetch_open3}


# ── Build helpers ─────────────────────────────────────────────────────────────

def by_abbr(df, abbrs):
    return df[df["TEAM_ABBREVIATION"].isin(abbrs)].copy()


def build_players(fetched, col, abbrs, top_n, per_team, po_rounds):
    primary_key = ROUND_KEY[max(po_rounds)]
    primary_df  = fetched[primary_key]

    base = by_abbr(primary_df, abbrs)[["PLAYER_NAME", "TEAM_ABBREVIATION", col]].rename(columns={col: primary_key})
    base = base.merge(
        by_abbr(fetched["rs"],   abbrs)[["PLAYER_NAME", col]].rename(columns={col: "rs"}),
        on="PLAYER_NAME", how="left",
    ).merge(
        by_abbr(fetched["post"], abbrs)[["PLAYER_NAME", col]].rename(columns={col: "post"}),
        on="PLAYER_NAME", how="left",
    )
    for r in po_rounds:
        key = ROUND_KEY[r]
        if key == primary_key:
            continue
        base = base.merge(
            by_abbr(fetched[key], abbrs)[["PLAYER_NAME", col]].rename(columns={col: key}),
            on="PLAYER_NAME", how="left",
        )

    all_keys = ["rs", "post"] + [ROUND_KEY[r] for r in po_rounds]
    for k in all_keys:
        base[k] = base[k].fillna(0).round(1)

    if per_team:
        chunks = [
            base[base["TEAM_ABBREVIATION"] == a].sort_values(primary_key, ascending=False).head(top_n)
            for a in abbrs
        ]
        base = pd.concat(chunks)
    else:
        base = base.sort_values(primary_key, ascending=False).head(top_n)

    result = []
    for _, row in base.iterrows():
        p = {"name": row["PLAYER_NAME"], "team": row["TEAM_ABBREVIATION"],
             "rs": float(row["rs"]), "post": float(row["post"])}
        for r in [1, 2, 3]:
            key = ROUND_KEY[r]
            p[key] = float(row[key]) if key in row.index and pd.notna(row.get(key)) else None
        result.append(p)
    return result


# ── Markdown printer ──────────────────────────────────────────────────────────

ROUND_LABEL = {"r1": "R1", "r2": "R2", "cf": "CF"}

def print_markdown(result):
    print("\n" + "=" * 70)
    print("STAT LEADER GUIDE")
    print("=" * 70)
    for entry in result:
        teams_str = " vs ".join(entry["teams"])
        rounds    = [k for k in ["r1", "r2", "cf"] if any(p[k] is not None for p in entry["players"])]
        print(f"\n## {teams_str} — {entry['stat']}\n")
        rh = "".join(f"| {ROUND_LABEL[k]:>7}" for k in rounds)
        rd = "".join(f"|{'-'*8}" for _ in rounds)
        print(f"| {'Player':<26}| {'Tm':<5}| {'RS Avg':>7}| {'Post-ASB':>9}{rh} |")
        print(f"|{'-'*27}|{'-'*6}|{'-'*8}|{'-'*10}{rd}|")
        for p in entry["players"]:
            rv = "".join(f"| {p[k]:>7.1f}" if p[k] is not None else "|     — " for k in rounds)
            print(f"| {p['name']:<26}| {p['team']:<5}| {p['rs']:>7.1f}| {p['post']:>9.1f}{rv} |")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--post", action="store_true")
    parser.add_argument("--out",  default="", help="save markdown to file")
    args = parser.parse_args()

    # Deduplicate fetches: (fetch_type, period_key) → df
    needed = {}
    for s in SERIES:
        ft = s["fetch"]
        needed[(ft, "rs")]   = None
        needed[(ft, "post")] = None
        for r in s.get("po_rounds", [1]):
            needed[(ft, ROUND_KEY[r])] = None

    fetched_dfs = {}
    for (ft, period) in needed:
        label = f"{ft} {period}"
        print(f"{label}...", flush=True)
        fn = FETCHERS[ft]
        if period == "rs":
            df = fn("Regular Season")
        elif period == "post":
            df = fn("Regular Season", season_segment="Post All-Star")
        else:
            round_num = {v: k for k, v in ROUND_KEY.items()}[period]
            df = fn("Playoffs", po_round=round_num)
        fetched_dfs[(ft, period)] = df

    result = []
    for s in SERIES:
        ft      = s["fetch"]
        fetched = {p: fetched_dfs[(ft, p)]
                   for p in ["rs", "post"] + [ROUND_KEY[r] for r in s.get("po_rounds", [1])]}
        players = build_players(
            fetched, s["col"], s["abbrs"],
            s["top_n"], s.get("per_team", False), s.get("po_rounds", [1]),
        )
        result.append({"teams": s["teams"], "stat": s["stat"], "players": players})

    print(json.dumps(result, indent=2))

    if args.out:
        import sys, io
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        print_markdown(result)
        sys.stdout = old_stdout
        with open(args.out, "w") as f:
            f.write(buf.getvalue())
        print(f"Saved to {args.out}", file=sys.stderr)

    if args.post:
        key = os.environ.get("INTERNAL_API_KEY", "")
        resp = requests.post(
            f"{BASE_URL}/admin/stat-guide",
            json={"matchups": result},
            headers={"Content-Type": "application/json", "X-Internal-Key": key},
            timeout=10,
        )
        print(f"POST /admin/stat-guide → {resp.status_code} {resp.text}", flush=True)


if __name__ == "__main__":
    main()
