"""Build the player page's static extras: bio (height, weight, age) and career honors.

    python3 scripts/build_player_extras.py --awards path/to/awards.json   (PlayerAwards rows keyed by player id)

Writes backend/fantasy_2026_27/data/player_bio.json and player_honors.json. Bio comes from
LeagueDashPlayerBioStats (one call per season, newest season wins); honors are counted per season.
"""
import argparse, json, time, unicodedata
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "backend" / "fantasy_2026_27" / "data"
HONORS = {"NBA Most Valuable Player": "mvp", "NBA Finals Most Valuable Player": "fmvp", "NBA Champion": "champ",
          "NBA Defensive Player of the Year": "dpoy", "All-NBA": "allnba", "NBA All-Star": "allstar",
          "All-Defensive Team": "alldef"}


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower().strip()


def bios(seasons):
    from nba_api.stats.endpoints import LeagueDashPlayerBioStats
    from nba_api.stats.library.http import NBAStatsHTTP
    out = {}
    for season in seasons:  # oldest first so the newest season overwrites
        for attempt in range(5):
            try:
                df = LeagueDashPlayerBioStats(season=season, timeout=60).get_data_frames()[0]
                break
            except Exception as e:
                print(season, "retry", attempt, e, flush=True)
                time.sleep(30 * (attempt + 1))
        else:
            continue
        end_year = int(season[:4]) + 1
        for r in df.to_dict("records"):
            out[str(r["PLAYER_ID"])] = {"ht": r["PLAYER_HEIGHT"], "wt": str(r["PLAYER_WEIGHT"]),
                                        "born": end_year - int(r["AGE"]) - 1}  # birth year, roughly
        print(season, len(df), flush=True)
        time.sleep(3)
    return out


def honors(awards):
    out = {}
    for pid, rows in awards.items():
        seen = {}
        for r in rows:
            k = HONORS.get(r["DESCRIPTION"])
            if k:
                seen.setdefault(k, set()).add(r["SEASON"])
        c = {k: len(v) for k, v in seen.items()}
        if c:
            out[pid] = c
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--awards")
    ap.add_argument("--skip-bio", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if not a.skip_bio:
        b = bios(["2022-23", "2023-24", "2024-25", "2025-26"])
        (OUT / "player_bio.json").write_text(json.dumps(b, separators=(",", ":")))
        print("bio", len(b))
    if a.awards:
        h = honors(json.loads(Path(a.awards).read_text()))
        (OUT / "player_honors.json").write_text(json.dumps(h, separators=(",", ":")))
        print("honors", len(h))
