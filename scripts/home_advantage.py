import requests, json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.nba.com/',
    'Accept': 'application/json',
}

BASE = "https://stats.nba.com/stats/leaguedashteamstats"

COMMON = dict(
    Season="2025-26", SeasonType="Regular Season", PerMode="PerGame",
    MeasureType="Advanced", LeagueID="00",
    PlusMinus="N", PaceAdjust="N", Rank="N",
    LastNGames=0, Month=0, OpponentTeamID=0, Period=0,
    DateFrom="", DateTo="",
)

# Pickem name → NBA API TEAM_NAME
TEAM_MAP = {
    "Detroit":       "Detroit Pistons",
    "Orlando":       "Orlando Magic",
    "Cleveland":     "Cleveland Cavaliers",
    "Toronto":       "Toronto Raptors",
    "New York":      "New York Knicks",
    "Atlanta":       "Atlanta Hawks",
    "Boston":        "Boston Celtics",
    "Philadelphia":  "Philadelphia 76ers",
    "Oklahoma City": "Oklahoma City Thunder",
    "LA Lakers":     "Los Angeles Lakers",
    "Houston":       "Houston Rockets",
    "Denver":        "Denver Nuggets",
    "Minnesota":     "Minnesota Timberwolves",
    "San Antonio":   "San Antonio Spurs",
    "Portland":      "Portland Trail Blazers",
    # Add 16th team (West 8-seed) once known
}

def fetch(location=""):
    params = {**COMMON}
    if location:
        params["Location"] = location
    r = requests.get(BASE, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    rs = r.json()["resultSets"][0]
    idx = {h: i for i, h in enumerate(rs["headers"])}
    return {
        row[idx["TEAM_NAME"]]: row[idx["NET_RATING"]]
        for row in rs["rowSet"]
    }

def main():
    print("Fetching overall NR...")
    overall = fetch()
    print("Fetching home NR...")
    home = fetch("Home")
    print("Fetching road NR...")
    road = fetch("Road")

    result = {}
    for pickem_name, api_name in TEAM_MAP.items():
        if api_name not in overall:
            print(f"WARNING: {api_name} not found in API response")
            continue
        o = overall[api_name]
        h = home.get(api_name, o)
        r = road.get(api_name, o)
        result[pickem_name] = {
            "home_adj": round(max(0.0, h - o), 2),
            "away_adj": round(min(0.0, r - o), 2),
            "_debug": {"home_NR": h, "road_NR": r, "overall_NR": o},
        }
        print(f"{pickem_name:20s}  home_adj={result[pickem_name]['home_adj']:5.2f}  away_adj={result[pickem_name]['away_adj']:5.2f}  (home={h:.1f}, road={r:.1f}, overall={o:.1f})")

    out = "/Users/allan/PycharmProjects/2026_pickem/team_home_away.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved → {out}")

if __name__ == "__main__":
    main()
