"""Shot chart fields for the player page's LED board (nba_shot_fields), the method of
nba-pipeline/analysis/shot_chart.py, cell for cell (TEAMMATE_EFFECT.md "Shot charts"):

- where: his shots smoothed at 1.5 ft, twos and threes separately with the kernel mass that falls across the line
  corrected, a 1.2-ft finish blur; the layers are the levels holding 95 / 80 / 60 / 40 / 20% of his shots.
- how well: his points per shot minus the league's from the same spot (both 4 ft, twos / threes apart), shrunk toward
  even where he has few shots nearby (n / (n + 6)), faded outside the area holding 90% of his shots, 1.2-ft blur.
Stored every 0.5 ft: lvl (one digit per cell: 0 = outside the 95% area, 1..5) and d = points vs league x100 where
lvl > 0. Used by the nightly job (from the stored play-by-play) and scripts/build_shot_fields.py (local check).

Shots are dicts / rows with x, y (tenths of a foot, hoop at 0,0), three (bool), pts (0 / 2 / 3).
"""
import math

import numpy as np

MIN_SHOTS = 50          # fewer in a season: no chart
HEAVE_FT = 40           # shots from farther are heaves, left out (the pipeline's play-by-play logged them separately)
STEP = 5                # stored cell = 0.5 ft
X0, X1, Y0, Y1 = -250, 250, -52, 420
NX, NY = X1 - X0, Y1 - Y0
S_WHERE, S_HOW = 15, 40
_gy, _gx = np.mgrid[Y0:Y1, X0:X1]
IS3 = (np.abs(_gx) >= 220) | (np.hypot(_gx, _gy) >= 237.5)
_e = np.clip(np.minimum.reduce([_gx - X0, X1 - 1 - _gx, _gy - Y0, Y1 - 1 - _gy]) / 20.0, 0, 1)
EDGE = _e * _e * (3 - 2 * _e)
_DEN: dict = {}


def blur(g, s):
    k = np.exp(-0.5 * (np.arange(-3 * s, 3 * s + 1) / s) ** 2); k /= k.sum()
    g = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, g)
    return np.apply_along_axis(lambda c: np.convolve(c, k, "same"), 0, g)


def _den(s):
    if s not in _DEN:
        _DEN[s] = (blur(IS3.astype(float), s), blur((~IS3).astype(float), s))
    return _DEN[s]


def _grid(x, y, w=None):
    g = np.zeros((NY, NX))
    np.add.at(g, (np.clip(y - Y0, 0, NY - 1).astype(int), np.clip(x - X0, 0, NX - 1).astype(int)), 1 if w is None else w)
    return g


def kde(x, y, three, s, w=None):
    """Kernel density of shots (or of w), twos smoothed only with twos and threes only with threes."""
    out = np.zeros((NY, NX))
    for m, sel, den in ((IS3, three, _den(s)[0]), (~IS3, ~three, _den(s)[1])):
        num = blur(_grid(x[sel], y[sel], None if w is None else w[sel]), s)
        out[m] = (num / np.maximum(den, 1e-9))[m]
    return out


def arrays(shots):
    x = np.array([s["x"] for s in shots], dtype=float); y = np.array([s["y"] for s in shots], dtype=float)
    return x, y, np.array([bool(s["three"]) for s in shots]), np.array([s["pts"] for s in shots], dtype=float)


def league_pps(shots):
    """The league's points per shot at every spot (4 ft)."""
    x, y, t, p = arrays(shots)
    return kde(x, y, t, S_HOW, p) / np.maximum(kde(x, y, t, S_HOW), 1e-9)


def _soft(field, level):
    v = np.clip(np.log(np.maximum(field, 1e-15) / level) / np.log(3) + 0.5, 0, 1)
    return v * v * (3 - 2 * v)


def field(shots, l_pps) -> dict:
    """One player-season's stored field."""
    x, y, t, p = arrays(shots)
    p_raw = kde(x, y, t, S_WHERE); p_d = p_raw / p_raw.sum()
    p_att, p_pts = kde(x, y, t, S_HOW), kde(x, y, t, S_HOW, p)
    n_how = p_att * 2 * math.pi * S_HOW ** 2
    delta = (p_pts / np.maximum(p_att, 1e-9) - l_pps) * (n_how / (n_how + 6))
    flat = np.sort(p_d.ravel())[::-1]
    delta = blur(delta * _soft(p_d, float(flat[np.searchsorted(np.cumsum(flat), 0.90)])) * EDGE, 12)
    dens = blur(p_d * EDGE, 12)
    dflat = np.sort(dens.ravel())[::-1]; dcum = np.cumsum(dflat) / dflat.sum()
    hdr = [float(dflat[np.searchsorted(dcum, q)]) for q in (0.95, 0.80, 0.60, 0.40, 0.20)]
    d5, f5 = dens[::STEP, ::STEP], delta[::STEP, ::STEP]
    lvl = sum((d5 >= h).astype(int) for h in hdr)
    return {"x0": X0, "y0": Y0, "step": STEP, "nx": int(d5.shape[1]), "ny": int(d5.shape[0]), "n": int(len(shots)),
            "lvl": "".join(map(str, lvl.ravel())), "d": [int(round(v * 100)) for v in f5[lvl > 0]]}


def shots_from_pbp(payload: dict) -> list:
    """Field goal attempts from one CDN play-by-play feed: {player_id, x, y, three, pts}; heaves left out."""
    out = []
    for a in (payload or {}).get("game", {}).get("actions", []):
        if a.get("isFieldGoal") != 1 or a.get("xLegacy") is None or a.get("yLegacy") is None:
            continue
        if (a.get("shotDistance") or 0) > HEAVE_FT:
            continue
        three = a.get("actionType") == "3pt"
        out.append({"player_id": str(a.get("personId")), "x": a["xLegacy"], "y": a["yLegacy"], "three": three,
                    "pts": (3 if three else 2) if a.get("shotResult") == "Made" else 0})
    return out


def shots_rows(payload: dict) -> list:
    """One game's shots in the stored compact form: [[player_id, x, y, three 0/1, pts], ...]."""
    return [[s["player_id"], s["x"], s["y"], 1 if s["three"] else 0, s["pts"]] for s in shots_from_pbp(payload)]


def from_rows(rows: list) -> list:
    return [{"player_id": r[0], "x": r[1], "y": r[2], "three": bool(r[3]), "pts": r[4]} for r in rows]


def build_all(shots: list) -> dict:
    """player id → field for every player with MIN_SHOTS+ shots, against the league map from all of `shots`."""
    if not shots:
        return {}
    l_pps = league_pps(shots)
    by = {}
    for s in shots:
        by.setdefault(s["player_id"], []).append(s)
    return {pid: field(ss, l_pps) for pid, ss in by.items() if len(ss) >= MIN_SHOTS}
