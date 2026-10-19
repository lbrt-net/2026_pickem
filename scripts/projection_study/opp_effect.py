"""Does the opponent / venue / rest move a player's game, beyond his own number? (commissioner, 2026-10-18)

The Roster page shows one number under every game (Haliburton 30.8 @ NOP, vs DAL, @ BKN). Question: would a number
adjusted for the opponent's strength, home/away and rest land closer to what he actually scores?

Every input is known before tip-off (no postdictors):
  baseline   his pre-game number under the site's rule: last season's FP/G moving onto his games so far this season,
             1/14 per game played (projections.blend). Last season stands in for the preseason PROJ AVG.
  opp_drtg   opponent's defensive rating so far (points allowed per 100 possessions), blended from its last season
             the same way (1/14 per game played).
  opp_pace   opponent's pace so far, same blend.
  opp_net    opponent's net rating so far, same blend (a strong team → blowouts → fewer minutes for starters?).
  opp_fpa    fantasy points the opponent gave up beyond players' own baselines, its games so far, same blend.
  home       1 at home.
  b2b        his team played yesterday.   opp_b2b  the opponent played yesterday.

Fit seasons '23–'25 ('22 is only the prior for '23); '26 is never used for fitting — it's the test.
Effects are multiplicative (a faster opponent scales his whole line): FP − baseline = baseline × Σ coef × feature.

    .venv/bin/python scripts/projection_study/opp_effect.py
"""
import json
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

from common import R, fp

SEASONS = ["2021-22", "2022-23", "2023-24", "2024-25", "2025-26"]
FIT, TEST = ["2022-23", "2023-24", "2024-25"], ["2025-26"]
FULL = 14  # projections.FULL_SEASON_GAMES


def blend(pre, vals):
    if not vals:
        return pre
    own = sum(vals) / len(vals)
    if pre is None:
        return own
    w = min(1.0, len(vals) / FULL)
    return (1 - w) * pre + w * own


def rows(path):
    rs = json.load(open(path))["resultSets"][0]
    h = rs["headers"]
    return [dict(zip(h, r)) for r in rs["rowSet"]]


def day(s):
    return date.fromisoformat(s[:10])


def line(r):
    return {"pts": r["PTS"], "fgm": r["FGM"], "fga": r["FGA"], "fg3m": r["FG3M"], "ftm": r["FTM"], "fta": r["FTA"],
            "oreb": r["OREB"], "dreb": r["DREB"], "ast": r["AST"], "stl": r["STL"], "blk": r["BLK"], "tov": r["TOV"],
            "blkd": r.get("BLKA") or 0}


def build():
    prev_fp = {}            # player -> last season FP/G
    prev_team = {}          # team -> {"drtg","pace","net","fpa"} last season
    lg_prev = None
    out = []
    for season in SEASONS:
        games = [r for r in rows(R + f"game_logs/{season}.json") if (r["MIN"] or 0) > 0]
        tl = rows(R + f"team_logs_advanced/{season}.json")
        tgame = {(r["GAME_ID"], r["TEAM_ABBREVIATION"]): r for r in tl}
        tdates = defaultdict(set)
        for r in tl:
            tdates[r["TEAM_ABBREVIATION"]].add(day(r["GAME_DATE"]))
        by_date = defaultdict(list)
        for r in games:
            by_date[day(r["GAME_DATE"])].append(r)
        own = defaultdict(list)                 # player -> FP this season so far
        tstate = defaultdict(lambda: {"drtg": [], "pace": [], "net": [], "fpa": []})
        for d in sorted(by_date):
            todays = []
            for r in by_date[d]:
                pid, team = r["PLAYER_ID"], r["TEAM_ABBREVIATION"]
                opp = r["MATCHUP"].split(" ")[-1]
                base = blend(prev_fp.get(pid), own[pid])
                x = fp(line(r))
                todays.append((r, x, base, opp))
                if base is None or base <= 0:
                    continue
                pt = prev_team.get(opp) or lg_prev or {}
                st = tstate[opp]
                out.append({"season": season, "pid": pid, "name": r["PLAYER_NAME"], "date": d, "team": team, "opp": opp,
                            "fp": x, "base": base, "n_own": len(own[pid]),
                            "opp_drtg": blend(pt.get("drtg"), st["drtg"]), "opp_pace": blend(pt.get("pace"), st["pace"]),
                            "opp_net": blend(pt.get("net"), st["net"]), "opp_fpa": blend(pt.get("fpa", 0.0), st["fpa"]) or 0.0,
                            "home": 0 if "@" in r["MATCHUP"] else 1,
                            "b2b": int(d - timedelta(days=1) in tdates[team]), "opp_b2b": int(d - timedelta(days=1) in tdates[opp])})
            # after the day: update states
            fpa_day = defaultdict(list)
            for r, x, base, opp in todays:
                own[r["PLAYER_ID"]].append(x)
                if base is not None:
                    fpa_day[(r["GAME_ID"], opp)].append(x - base)
            for (gid, opp), res in fpa_day.items():
                tstate[opp]["fpa"].append(sum(res))  # per game: total FP given up beyond expectation
            seen = set()
            for r in by_date[d]:
                k = (r["GAME_ID"], r["TEAM_ABBREVIATION"])
                if k in seen or k not in tgame:
                    continue
                seen.add(k)
                t = tgame[k]
                s = tstate[t["TEAM_ABBREVIATION"]]
                s["drtg"].append(t["DEF_RATING"])
                s["pace"].append(t["PACE"])
                s["net"].append(t["NET_RATING"])
        # end of season → priors for next season
        tot = defaultdict(list)
        for pid, v in own.items():
            tot[pid] = v
        prev_fp = {pid: sum(v) / len(v) for pid, v in tot.items() if v}
        prev_team = {t: {k: (sum(v) / len(v) if v else None) for k, v in s.items()} for t, s in tstate.items()}
        lg_prev = {k: float(np.mean([p[k] for p in prev_team.values() if p[k] is not None])) for k in ("drtg", "pace", "net", "fpa")}
    return out


FEATS = ["opp_drtg", "opp_pace", "opp_net", "opp_fpa", "home", "b2b", "opp_b2b"]


def design(rs, means):
    # centred features (league average opponent = 0), each scaled by the baseline: effects are proportional
    X = np.array([[r["base"] * (r[f] - means[f]) for f in FEATS] + [r["base"]] for r in rs])
    return X


def main():
    data = build()
    fit = [r for r in data if r["season"] in FIT]
    test = [r for r in data if r["season"] in TEST]
    means = {f: float(np.mean([r[f] for r in fit])) for f in FEATS}
    X, y = design(fit, means), np.array([r["fp"] - r["base"] for r in fit])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    print(f"player-games: fit {len(fit)}, test {len(test)}")
    print("\nper-feature effect (as % of his own number, per unit of the feature):")
    sd = {f: float(np.std([r[f] for r in fit])) for f in FEATS}
    for f, c in zip(FEATS, coef):
        print(f"  {f:9s} {c * 100:+.3f}% per unit   one-SD opponent ({sd[f]:.2f}) = {c * sd[f] * 100:+.2f}%")
    print(f"  baseline bias {coef[-1] * 100:+.2f}%")

    def score(rs, use):
        Xt = design(rs, means)
        y = np.array([r["fp"] for r in rs])
        b = np.array([r["base"] for r in rs])
        pred = b + Xt[:, -1] * coef[-1] + (Xt[:, :-1] @ coef[:-1] if use else 0)
        e = y - pred
        return np.mean(np.abs(e)), np.sqrt(np.mean(e ** 2))

    for name, rs in (("fit '23–'25", fit), ("TEST '26", test)):
        a0, r0 = score(rs, False)
        a1, r1 = score(rs, True)
        print(f"\n{name}: avg miss per game  own number {a0:.3f} → with opponent/venue/rest {a1:.3f} FP"
              f"  (root-mean-square {r0:.3f} → {r1:.3f})")
    # per-season stability of each effect
    print("\neach effect fit season by season (same sign every year = real):")
    for s in FIT + TEST:
        rs = [r for r in data if r["season"] == s]
        c, *_ = np.linalg.lstsq(design(rs, means), np.array([r["fp"] - r["base"] for r in rs]), rcond=None)
        print("  " + s + "  " + "  ".join(f"{f}:{c[i] * sd[f] * 100:+.2f}%" for i, f in enumerate(FEATS)))
    # describe in real units: actual vs own number, by opponent quintile, test season
    print("\nreal rates, '26 (never fit): actual FP minus his own number, by opponent group")
    for f in ("opp_drtg", "opp_pace", "opp_fpa", "opp_net"):
        v = sorted(test, key=lambda r: r[f])
        q = len(v) // 5
        parts = []
        for i in range(5):
            g = v[i * q:(i + 1) * q]
            parts.append(f"{np.mean([r['fp'] - r['base'] for r in g]):+.2f}")
        print(f"  {f:9s} lowest→highest fifth: " + "  ".join(parts))
    for f in ("home", "b2b", "opp_b2b"):
        for val in (1, 0):
            g = [r for r in test if r[f] == val]
            print(f"  {f}={val}: {np.mean([r['fp'] - r['base'] for r in g]):+.2f} FP  ({len(g)} games)")
    json.dump({"coef": dict(zip(FEATS + ["bias"], map(float, coef))), "means": means},
              open(str(__import__("common").WORK / "opp_effect_coef.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
