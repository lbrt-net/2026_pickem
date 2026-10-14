"""Balanced matchup schedule (commissioner, 2026-10-12): every team should face about the same strength of schedule.

- Strength = the manager's average win % over the last 3 fantasy seasons on record (fantasy_manager_seasons, seeded from
  the standings in ROADMAP.md, edited in League Settings → Past seasons); a season he wasn't in counts as .400. New
  managers = .400. A team is matched to its manager by Discord account, else by name / aliases.
- Candidates: the round robin (circle method; an odd team count gives one bye a week) with the teams shuffled and the
  rounds of each cycle in a random order, laid over the regular-season weeks. Kept: byes as even as possible, the extra
  byes on the strongest teams (a bye doesn't change expected win %, but fewer games = more luck and less total points
  for, so it handicaps the strong), then the smallest spread in each team's average opponent strength.
- Written as the commissioner's week-by-week matchups (engine.set_matchups), so League Settings → Matchups shows and
  can still edit them. Runs when the draft completes (all teams known) if the league's matchup schedule is "balanced"
  (the default), and from League Settings → Matchups → Balance now (commissioner).
"""
import random
import statistics

from . import engine

DEFAULT = 0.400  # a season a manager wasn't in, and new managers
SEASONS_COUNTED = 3

# The commissioner's standings (ROADMAP.md, 2026-10-12), seeded once into fantasy_manager_seasons:
# (season, manager, discord id, aliases, team name, wins, losses)
_E, _WO, _DE, _MI = "97705344175702016", "91556991276699648", "149247446759768064", "148225059696148480"
_NO, _AP, _CH, _SS = "186984468991574016", "93280783308951552", "183328043488509953", "186970106557890560"
SEED = [
    ("2025-26", "elbert", _E, None, None, 12, 5), ("2025-26", "cody", None, None, "Hot Shooters", 11, 6),
    ("2025-26", "deco", _DE, None, "Decorations", 10, 6), ("2025-26", "wonton", _WO, None, None, 10, 6),
    ("2025-26", "king midas", None, "kingmidasw", "Kingmidasw", 9, 7), ("2025-26", "awesomeus prime", _AP, None, None, 9, 7),
    ("2025-26", "nana", None, "hannaioop,kachowlmao", "hannaioop", 9, 7), ("2025-26", "chika", _CH, "chikaguya", "chikaguya", 9, 8),
    ("2025-26", "mits", _MI, "mitsol", "Mitsol", 5, 11), ("2025-26", "nacho", None, "nachodemacho", "nachodemacho", 4, 12),
    ("2025-26", "weinis", None, "weinis_", "Weinis_", 2, 15),
    ("2024-25", "wonton", _WO, None, "Kung Fu Panda Coco Pops", 11, 2), ("2024-25", "elbert", _E, None, "el bane mercenario", 10, 3),
    ("2024-25", "mits", _MI, "mitsol", "The Sassy Sloth Squad", 9, 4), ("2024-25", "notre", _NO, "notretower", "Notretower", 9, 4),
    ("2024-25", "nana", None, "hannaioop,kachowlmao", "dick and friends", 8, 5), ("2024-25", "deco", _DE, None, "Decorations", 7, 6),
    ("2024-25", "gashee", None, None, "Team Normal", 7, 6), ("2024-25", "kitten", None, None, "Tang's Discord Cats", 6, 7),
    ("2024-25", "cody", None, None, "Real Fowl", 6, 7), ("2024-25", "silversephiroth", _SS, "darius", "SilverSephiroth", 4, 9),
    ("2024-25", "chika", _CH, "chikaguya", "jordan poole fan club: revitalization", 4, 9),
    ("2024-25", "reptar", None, None, "Decorations slayer", 4, 9), ("2024-25", "lunar", None, "zuotiandenixi", "zuotiandenixi", 3, 10),
    ("2024-25", "weinis", None, "weinis_", "Weinis_", 3, 10),
    ("2023-24", "elbert", _E, None, "elk berts", 13, 5), ("2023-24", "reptar", None, None, "steve reptar", 13, 5),
    ("2023-24", "deco", _DE, None, "Pogsketball", 11, 7), ("2023-24", "mits", _MI, "mitsol", "POGGIES THE EMPIRE STRIKES BACK", 11, 7),
    ("2023-24", "wonton", _WO, None, "Flaunting Boomerang Godzillas", 9, 9), ("2023-24", "chika", _CH, "chikaguya", "jordan poole fanclub", 9, 9),
    ("2023-24", "nana", None, "hannaioop,kachowlmao", "hannaioop", 9, 9), ("2023-24", "lunar", None, "zuotiandenixi", "zuotiandenixi", 8, 10),
    ("2023-24", "cody", None, None, "Not reptar for way too long man", 4, 14), ("2023-24", "weinis", None, "weinis_", "Weinis_", 3, 15),
]


def history(cur) -> dict:
    """{"seasons": the last 3 seasons on record (newest first), "managers": [{manager, discord_id, aliases, records:
    {season: [w, l]}, strength}]} from fantasy_manager_seasons."""
    cur.execute("SELECT DISTINCT season FROM fantasy_manager_seasons ORDER BY season DESC LIMIT %s", (SEASONS_COUNTED,))
    seasons = [r["season"] for r in cur.fetchall()]
    cur.execute("SELECT * FROM fantasy_manager_seasons ORDER BY manager, season DESC")
    by = {}
    for r in cur.fetchall():
        m = by.setdefault(r["manager"], {"manager": r["manager"], "discord_id": None, "aliases": "", "records": {}})
        m["discord_id"] = m["discord_id"] or r["discord_id"]
        m["aliases"] = m["aliases"] or (r["aliases"] or "")
        m["records"][r["season"]] = [r["wins"], r["losses"]]
    for m in by.values():
        pct = [(w / (w + l) if w + l else DEFAULT) for w, l in (m["records"].get(s, (None, None)) for s in seasons) if w is not None]
        pct += [DEFAULT] * (len(seasons) - len(pct))
        m["strength"] = round(sum(pct) / len(pct), 3) if pct else DEFAULT
    return {"seasons": seasons, "managers": sorted(by.values(), key=lambda m: -m["strength"])}


def save_history(cur, managers: list) -> dict:
    """Replace the past-seasons records (League Settings → Past seasons). managers = [{manager, discord_id, aliases,
    records: {season: [w, l]}}]."""
    rows = []
    for m in managers:
        name = (m.get("manager") or "").strip()
        if not name:
            continue
        for season, wl in (m.get("records") or {}).items():
            if not wl or wl[0] in (None, "") or wl[1] in (None, ""):
                continue
            w, l = int(wl[0]), int(wl[1])
            if w < 0 or l < 0:
                raise ValueError(f"{name} {season}: wins and losses can't be negative")
            rows.append((season.strip(), name, (m.get("discord_id") or "").strip() or None, (m.get("aliases") or "").strip() or None, w, l))
    cur.execute("DELETE FROM fantasy_manager_seasons")
    for r in rows:
        cur.execute("""INSERT INTO fantasy_manager_seasons (season, manager, discord_id, aliases, wins, losses)
                       VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (season, manager) DO UPDATE SET wins = EXCLUDED.wins,
                       losses = EXCLUDED.losses, discord_id = EXCLUDED.discord_id, aliases = EXCLUDED.aliases""", r)
    return history(cur)


def strength_for(team: dict, hist: dict) -> tuple:
    """(strength, matched manager or None) for a league team: by Discord account, else by name (manager, aliases)
    appearing in the owner's username or the team name."""
    for m in hist["managers"]:
        if m["discord_id"] and m["discord_id"] == team.get("owner_user_id"):
            return m["strength"], m["manager"]
    keys = [(team.get("owner_name") or "").lower(), (team.get("name") or "").lower()]
    for m in hist["managers"]:
        names = [m["manager"].lower()] + [a.strip().lower() for a in (m["aliases"] or "").split(",") if a.strip()]
        if any(n and n in k for n in names for k in keys):
            return m["strength"], m["manager"]
    return DEFAULT, None


def _rounds(ids: list) -> list[list[tuple]]:
    ids = list(ids) + ([None] if len(ids) % 2 else [])
    n, out = len(ids), []
    for r in range(n - 1):
        rot = [ids[0]] + ids[1:][r:] + ids[1:][:r]
        out.append([(rot[i], rot[n - 1 - i]) for i in range(n // 2)])
    return out


def build(teams: list[dict], n_weeks: int, tries: int = 20000, seed: int = 2026) -> tuple[list[list[tuple]], dict]:
    """Best of `tries` candidate schedules: (weeks of pairs with None = bye, report). Each team dict carries its
    `strength`."""
    rng = random.Random(seed)
    s = {t["id"]: t["strength"] for t in teams}
    ids = [t["id"] for t in teams]
    best, best_key = None, None
    for _ in range(tries):
        order = ids[:]
        rng.shuffle(order)
        rounds = _rounds(order)
        weeks = []
        while len(weeks) < n_weeks:
            cyc = rounds[:]
            rng.shuffle(cyc)
            weeks += cyc
        weeks = weeks[:n_weeks]
        opp, byes = {i: [] for i in ids}, {i: 0 for i in ids}
        for wk in weeks:
            for a, b in wk:
                if a is None or b is None:
                    byes[a or b] += 1
                else:
                    opp[a].append(s[b])
                    opp[b].append(s[a])
        means = [statistics.mean(v) for v in opp.values() if v]
        # extra byes go to the strongest teams (fewer games = more luck in their record and less total points for — a
        # handicap): count pairs where a weaker team has more byes than a stronger one
        strong_first = sorted(ids, key=lambda i: -s[i])
        misplaced = sum(1 for a in range(len(ids)) for b in range(a + 1, len(ids)) if byes[strong_first[b]] > byes[strong_first[a]])
        key = (max(byes.values()) - min(byes.values()), misplaced, round(max(means) - min(means), 4))
        if best_key is None or key < best_key:
            best, best_key = (weeks, opp, byes), key
    weeks, opp, byes = best
    report = {i: {"strength": s[i], "opp_avg": round(statistics.mean(opp[i]), 3) if opp[i] else None, "games": len(opp[i]), "byes": byes[i]}
              for i in ids}
    return weeks, {"spread": best_key[2], "teams": report}


def apply(cur, scenario: str) -> dict:
    """Balance and save the regular-season schedule for the league's current teams."""
    lg = engine.league(cur, scenario)
    reg = [w for w in engine.weeks_for_league(cur, lg) if w["kind"] == "regular"]
    cur.execute("SELECT t.id, t.name, t.owner_user_id, u.username AS owner_name FROM fantasy_teams t LEFT JOIN users u ON u.discord_id = t.owner_user_id WHERE t.scenario = %s", (scenario,))
    teams = [dict(r) for r in cur.fetchall()]
    hist = history(cur)
    for t_ in teams:
        t_["strength"], t_["manager"] = strength_for(t_, hist)
    if len(teams) < 2 or not reg:
        return {"ok": False, "reason": "need 2+ teams and a regular season"}
    weeks, report = build(teams, len(reg))
    ids = {t["id"] for t in teams}
    for w, pairs in zip(reg, weeks):
        engine.set_matchups(cur, scenario, w["week"], [[a, b] for a, b in pairs if a and b], ids)
    names = {t["id"]: t["name"] for t in teams}
    manager = {t["id"]: t["manager"] for t in teams}
    report["teams"] = {names[k]: {**v, "manager": manager[k]} for k, v in report["teams"].items()}
    return {"ok": True, "weeks": len(reg), **report}
