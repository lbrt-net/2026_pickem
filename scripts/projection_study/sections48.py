# Sections 4–8, exec'd inside build_report4.py (uses its scatter / table / hbars / E / pc / f1 helpers).
D48 = json.load(open(S + "sec48.json"))
RW = [r for r in D48["rows"] if r["last"]]
EIGHT = D48["eight"]
ROT = [r for r in RW if r["act"]["mpg"] >= 20 and r["act"]["gp"] >= 40]  # rotation players for named lists
for r in RW:
    r["grp"] = "moved" if r["moved"] else "stable"
mkey = '<div class="key"><span><i class="g1"></i>Same team</span><span><i class="g2"></i>Changed teams</span><span><i class="bandkey"></i>close band</span></div>'
MG = {"stable": "g1", "moved": "g2"}


def pts(key, f, rows=RW):
    """flatten: name, grp, last, proj, act for one derived quantity f(section_dict)"""
    out = []
    for r in rows:
        try:
            l_, p_, a_ = f(r["last"]), f(r["proj"]), f(r["act"])
        except (TypeError, ZeroDivisionError, IndexError):
            continue
        if None in (l_, p_, a_) or any(v != v for v in (l_, p_, a_)):
            continue
        out.append(dict(name=r["name"], grp=r["grp"], last=l_, proj=p_, act=a_, mpg=r["act"]["mpg"], gp=r["act"]["gp"]))
    return out


def count(rows, k, tol):
    return sum(abs(x[k] - x["act"]) <= tol for x in rows)


def corr(rows, k):
    a = np.array([x[k] for x in rows]); b = np.array([x["act"] for x in rows])
    return float(np.corrcoef(a, b)[0, 1])


def misses(rows, n=6, fmt=f1, rot=True):
    rr = [x for x in rows if (x["mpg"] >= 20 and x["gp"] >= 40) or not rot]
    rr = sorted(rr, key=lambda x: x["proj"] - x["act"])
    head = ["Player", "'25", "Projected '26", "Actual '26"]
    under = table(head, [[E(x["name"]), fmt(x["last"]), f"<b>{fmt(x['proj'])}</b>", fmt(x["act"])] for x in rr[:n]])
    over = table(head, [[E(x["name"]), fmt(x["last"]), f"<b>{fmt(x['proj'])}</b>", fmt(x["act"])] for x in rr[::-1][:n]])
    return under, over


def works(rows, tol, n=8, fmt=f1):
    rr = sorted([x for x in rows if x["mpg"] >= 30 and x["gp"] >= 50 and abs(x["proj"] - x["act"]) <= tol], key=lambda x: -x["mpg"])[:n]
    return table(["Player", "'25", "Projected '26", "Actual '26"], [[E(x["name"]), fmt(x["last"]), f"<b>{fmt(x['proj'])}</b>", fmt(x["act"])] for x in rr])


def pair_sc(rows, lo, hi, lab, labels, band, fmt=f1, title_last="Last season vs what happened", title_proj="Projection vs what happened"):
    return (scatter(rows, "last", "act", lo, hi, f"'25 {lab}", f"'26 actual {lab}", labels, band=band, groups=MG, fmt=fmt, title=title_last)
            + scatter(rows, "proj", "act", lo, hi, f"projected {lab}", f"'26 actual {lab}", labels, band=band, groups=MG, fmt=fmt, title=title_proj))


pct0 = lambda v: f"{v * 100:.0f}%"  # noqa: E731
pct1 = lambda v: f"{v * 100:.1f}%"  # noqa: E731

# ---------------- 4. shooting
three = pts("three", lambda s: (s["share"][3] + s["share"][4]) if s and s.get("share") else None)
for x in three:
    x["last"], x["proj"], x["act"] = x["last"] * 100, x["proj"] * 100, x["act"] * 100
c3_last, c3_proj = count(three, "last", 5), count(three, "proj", 5)
LAB3 = {"Onyeka Okongwu", "Donovan Clingan", "Andre Drummond", "Nikola Jokić", "Jalen Brunson", "Kevin Durant"}
sc_three = scatter(three, "last", "act", 0, 90, "'25 share of shots from 3 (%)", "'26 share from 3 (%)", LAB3, band=5, groups=MG,
                   fmt=lambda v: f"{v:.0f}", title="Share of shots from 3: '25 vs '26")
mix_chg = sorted([x for x in three if x["mpg"] >= 20 and x["gp"] >= 40], key=lambda x: -abs(x["act"] - x["last"]))[:8]
mix_tbl = table(["Player", "'25 from 3", "Projected '26", "Actual '26"], [[E(x["name"]), f"{x['last']:.0f}%", f"<b>{x['proj']:.0f}%</b>", f"{x['act']:.0f}%"] for x in mix_chg])


def p3(s, is_proj):
    if is_proj:
        w = np.array(s["share"][3:]); z = np.array(s["zpct"][3:])
        return float((w * z).sum() / w.sum()) if w.sum() else None
    za = np.array(s["zatt"][3:]); zp = np.array([v or 0 for v in s["zpct"][3:]])
    return float((za * zp).sum() / za.sum()) if za.sum() else None


p3rows = []
for r in RW:
    if not r["act"]["zatt"] or sum(r["act"]["zatt"][3:]) < 150 or not r["last"]["zatt"]:
        continue
    l_, p_, a_ = p3(r["last"], False), p3(r["proj"], True), p3(r["act"], False)
    if None in (l_, p_, a_):
        continue
    p3rows.append(dict(name=r["name"], grp=r["grp"], last=l_ * 100, proj=p_ * 100, act=a_ * 100, mpg=r["act"]["mpg"], gp=r["act"]["gp"]))
c3p_l, c3p_p, n3p = count(p3rows, "last", 3), count(p3rows, "proj", 3), len(p3rows)
LABP = {"Jaylon Tyson", "Cam Spencer", "Alex Caruso", "De'Anthony Melton", "Stephen Curry", "Grayson Allen"}
sc_p3 = pair_sc(p3rows, 20, 50, "3P%", LABP, 3, fmt=lambda v: f"{v:.0f}")
p3_under, p3_over = misses(p3rows, fmt=lambda v: f"{v:.1f}%")
fgp = pts("fg", lambda s: s["fg_pct"] * 100 if s and s.get("fg_pct") else None)
cfg_l, cfg_p = count(fgp, "last", 3), count(fgp, "proj", 3)
fga = pts("fga75", lambda s: s["fga75"])
cfa_l, cfa_p = count(fga, "last", 1.5), count(fga, "proj", 1.5)
sc_fga = scatter(fga, "proj", "act", 0, 32, "projected FGA per 75", "'26 actual FGA per 75", {"Dillon Brooks", "Michael Porter Jr.", "Shai Gilgeous-Alexander", "Grayson Allen", "Nikola Jokić"},
                 band=1.5, groups=MG, title="Shot volume: projection vs what happened")
fga_under, fga_over = misses(fga)
e4 = table(["#", "Player", "From 3", "FGA", "FG%", "3PM / 3PA", "Points"],
           [[str(i + 1), E(e["name"]), pct0(e["proj"]["share"][3] + e["proj"]["share"][4]), f1(e["proj"]["fga"]), pct1(e["proj"]["fgm"] / e["proj"]["fga"]),
             f"{e['proj']['fg3m']:.1f} / {e['proj']['fg3a']:.1f}", f"<b>{f1(e['proj']['pts'])}</b>"] for i, e in enumerate(EIGHT)])

# ---------------- 5. free throws
fta = pts("fta75", lambda s: s["fta75"])
cft_l, cft_p = count(fta, "last", 1.0), count(fta, "proj", 1.0)
sc_fta = scatter(fta, "proj", "act", 0, 14, "projected FTA per 75", "'26 actual FTA per 75", {"Deni Avdija", "Jalen Duren", "Victor Wembanyama", "Jaylen Brown", "Shai Gilgeous-Alexander"},
                 band=1.0, groups=MG, title="Free-throw attempts: projection vs what happened")
fta_under, fta_over = misses(fta)
ftp = [x for x in pts("ftp", lambda s: s["ft_pct"] * 100 if s and s.get("ft_pct") else None)]
ftp = [x for x in ftp if next(r for r in RW if r["name"] == x["name"])["act"]["fta"] * x["gp"] >= 100]
cfp_l, cfp_p, nfp = count(ftp, "last", 3), count(ftp, "proj", 3), len(ftp)
sc_ftp = pair_sc(ftp, 50, 100, "FT%", {"Nickeil Alexander-Walker", "Ja Morant", "Rudy Gobert", "Duncan Robinson", "Stephen Curry"}, 3, fmt=lambda v: f"{v:.0f}")
ftp_under, ftp_over = misses(ftp, fmt=lambda v: f"{v:.1f}%")
e5 = table(["#", "Player", "FTA", "FT%", "FTM"], [[str(i + 1), E(e["name"]), f1(e["proj"]["fta"]), pct1(e["proj"]["ft_pct"]),
                                                  f"<b>{f1(e['proj']['fta'] * e['proj']['ft_pct'])}</b>"] for i, e in enumerate(EIGHT)])

# ---------------- 6. rebounding
orb = pts("oreb75", lambda s: s["oreb75"])
drb = pts("dreb75", lambda s: s["dreb75"])
co_l, co_p = count(orb, "last", 0.5), count(orb, "proj", 0.5)
cd_l, cd_p = count(drb, "last", 1.0), count(drb, "proj", 1.0)
sc_reb = (scatter(orb, "proj", "act", 0, 7, "projected OREB per 75", "'26 actual OREB per 75", {"Ariel Hukporti", "Mitchell Robinson", "Steven Adams", "Jalen Duren"}, band=0.5, groups=MG, title="Offensive rebounds")
          + scatter(drb, "proj", "act", 0, 16, "projected DREB per 75", "'26 actual DREB per 75", {"Hunter Tyson", "Mitchell Robinson", "Nikola Jokić", "Clint Capela"}, band=1.0, groups=MG, title="Defensive rebounds"))
shifted = [r for r in RW if abs(r["proj"]["dreb_shift"]) >= 0.005 and r["last"].get("dreb_pct") is not None]
right_d = sum(r["proj"]["dreb_shift"] * (r["act"]["dreb_pct"] - r["last"]["dreb_pct"]) > 0 for r in shifted)
ds_tbl = table(["Player", "'26 team", "Teammate effect", "'25 DREB%", "'26 DREB%"],
               [[E(r["name"]), r["team"] or "", f"{100 * r['proj']['dreb_shift']:+.1f}", pct1(r["last"]["dreb_pct"]), f"<b>{pct1(r['act']['dreb_pct'])}</b>"]
                for r in sorted(shifted, key=lambda r: -abs(r["proj"]["dreb_shift"]))[:10]])
drb_under, drb_over = misses(drb)
e6 = table(["#", "Player", "OREB", "DREB", "Teammate effect on DREB%"],
           [[str(i + 1), E(e["name"]), f1(e["proj"]["oreb"]), f"<b>{f1(e['proj']['dreb'])}</b>", f"{100 * e['proj']['dreb_shift']:+.1f}"] for i, e in enumerate(EIGHT)])

# ---------------- 7. assists, steals, blocks, turnovers
q = {k: pts(k, lambda s, k=k: s[k]) for k in ["ast75", "stl75", "blk75", "tov75"]}
TOL = {"ast75": 1.0, "stl75": 0.3, "blk75": 0.3, "tov75": 0.4}
HI = {"ast75": 14, "stl75": 3.5, "blk75": 4, "tov75": 5.5}
NM = {"ast75": "Assists", "stl75": "Steals", "blk75": "Blocks", "tov75": "Turnovers"}
LB = {"ast75": {"Cam Spencer", "Jalen Johnson", "Stephon Castle", "Zion Williamson", "Brandon Ingram"}, "stl75": {"Matisse Thybulle", "Dyson Daniels", "Cam Christie"},
      "blk75": {"Victor Wembanyama", "Clint Capela", "Yves Missi"}, "tov75": {"Jaylen Brown", "Cole Anthony", "Jaden Ivey"}}
sc7 = "".join(scatter(q[k], "proj", "act", 0, HI[k], f"projected {NM[k].lower()} per 75", "'26 actual", LB[k], band=TOL[k], groups=MG, title=NM[k]) for k in q)
t7 = table(["Per 75 possessions", "Close band", "Last season", "Projection", "Carries over (last → proj)", "How it's projected"],
           [[NM[k], f"±{TOL[k]}", str(count(q[k], 'last', TOL[k])), f"<b>{count(q[k], 'proj', TOL[k])}</b>", f"{corr(q[k], 'last'):.2f} → {corr(q[k], 'proj'):.2f}",
             {"ast75": "3 seasons, heavy on the latest", "stl75": "3 seasons pooled equally", "blk75": "3 seasons, heavy on the latest", "tov75": "3 seasons + usage"}[k]] for k in q])
ast_under, ast_over = misses(q["ast75"])
e7 = table(["#", "Player", "AST", "STL", "BLK", "TOV"], [[str(i + 1), E(e["name"]), f1(e["proj"]["ast"]), f"{e['proj']['stl']:.2f}", f"{e['proj']['blk']:.2f}",
                                                          f"{e['proj']['tov']:.2f}"] for i, e in enumerate(EIGHT)])

# ---------------- 8. own shots blocked
bk = pts("blkd", lambda s: s["blkd"])
cb_l, cb_p = count(bk, "last", 0.15), count(bk, "proj", 0.15)
sc_bk = pair_sc(bk, 0, 2, "own shots blocked per game", {"Zion Williamson", "Alex Sarr", "Jalen Duren", "Cade Cunningham", "Jeremy Sochan"}, 0.15,
                fmt=lambda v: f"{v:.1f}")
bk_under, bk_over = misses(bk, fmt=lambda v: f"{v:.2f}")
fac = sorted([r for r in RW if r["act"]["mpg"] >= 20], key=lambda r: r["proj"]["blkd_factor"])
fac_tbl = table(["Least blocked for their shots", "Factor", "Most blocked for their shots", "Factor"],
                [[E(a["name"]), f"{a['proj']['blkd_factor']:.2f}", E(b["name"]), f"{b['proj']['blkd_factor']:.2f}"] for a, b in zip(fac[:6], fac[::-1][:6])])
e8 = table(["#", "Player", "Own shots blocked", "FP cost"], [[str(i + 1), E(e["name"]), f"{e['proj']['blkd']:.2f}", f"<b>{-0.5 * e['proj']['blkd']:+.2f}</b>"] for i, e in enumerate(EIGHT)])

sec48_html = f"""
<section id="shooting"><div class="n">4</div><div><h2>Shooting: where shots come from and how often they go in</h2>
<p>Points from the field = shots × the share from each zone × the make rate in that zone × 2 or 3. Five zones: rim, rest of the paint, mid-range, corner 3, above-the-break 3. Shot volume comes from usage (section 3); this section is the mix and the make rates.</p>
<h3>The shot mix is a player's signature</h3>
<p class="claim">Where a player shoots from barely changes year to year. The misses are players whose role changed.</p>
{mkey}
<div class="pair">{sc_three}<div><p>Share of a player's shots from 3, '25 against '26. The two seasons track almost one for one: {c3_last} of {len(three)} players within 5 points. Weighting the year before (each season counts 5× the one before) changes little: {c3_proj} within 5 points. A trend line was tried and dropped; it chased one-off seasons.</p>
<p>The biggest moves among rotation players: bigs who started shooting 3s (Okongwu, Clingan), guards who took fewer (Jenkins, Pritchard, Melton), and wings who took more (Ja'Kobe Walter):</p>{mix_tbl}</div></div>
<h3>3-point percentage barely carries over</h3>
<p class="claim">A player's 3P% one season tells you little about the next. Three seasons pooled, pulled lightly toward the league rate, does much better.</p>
<div class="pair">{sc_p3}</div>
<p class="cap">Players with 150+ 3-point attempts in '26. Last season alone: {c3p_l} of {n3p} within 3 points (carry-over {corr(p3rows, 'last'):.2f}). Projection: {c3p_p} of {n3p} ({corr(p3rows, 'proj'):.2f}). The pull is light: 25 league-average shots, none once a player has 200+ attempts in a zone.</p>
<div class="pair"><div><p><b>Shot better than projected</b></p>{p3_under}</div><div><p><b>Shot worse than projected</b></p>{p3_over}</div></div>
<p>Overall FG% follows from the zone mix, so when a player's shots move, his FG% moves with them: {cfg_p} of {len(fgp)} within 3 points of actual FG%, against {cfg_l} for last season's FG%.</p>
<h3>Shot volume</h3>
<div class="pair">{sc_fga}<div><p>Shots per 75 possessions, with the usage adjustment from section 3: {cfa_p} of {len(fga)} within 1.5 shots, against {cfa_l} for last season's rate. The misses are players who got a bigger or smaller role after a move or an injury next to them.</p></div></div>
<div class="pair"><div><p><b>Shot more than projected</b></p>{fga_under}</div><div><p><b>Shot less than projected</b></p>{fga_over}</div></div>
<p class="cap">Named lists show rotation players (20+ minutes, 40+ games) so a few games of a fringe player don't crowd them out.</p>
<h3>2026-27: the random eight</h3>{e4}
</div></section>

<section id="ft"><div class="n">5</div><div><h2>Free throws</h2>
<p>Free-throw attempts per 75 possessions come from three seasons weighted toward the latest, scaled by usage. FT% pools three seasons and only pulls toward 79% for players with under 200 attempts.</p>
<h3>Getting to the line</h3>
<div class="pair">{sc_fta}<div><p>{cft_p} of {len(fta)} within one attempt per 75, against {cft_l} for last season's rate. The players who got to the line far more than projected were taking on bigger roles: Avdija, Duren, Wembanyama, Jaylen Brown.</p></div></div>
<div class="pair"><div><p><b>Got to the line more</b></p>{fta_under}</div><div><p><b>Got there less</b></p>{fta_over}</div></div>
<h3>FT% is a skill, but one season is a small sample</h3>
<p class="claim">Pooling three seasons makes free-throw percentage far more predictable than last season's number alone.</p>
<div class="pair">{sc_ftp}</div>
<p class="cap">Players with 100+ free throws in '26. Last season: {cfp_l} of {nfp} within 3 points. Projection: {cfp_p} of {nfp}.</p>
<div class="pair"><div><p><b>Shot better than projected</b></p>{ftp_under}</div><div><p><b>Shot worse</b></p>{ftp_over}</div></div>
<h3>2026-27: the random eight</h3>{e5}
</div></section>

<section id="rebounding"><div class="n">6</div><div><h2>Rebounding</h2>
<p class="claim">Offensive rebounding belongs to the player. Defensive rebounding is shared with the teammates on the floor.</p>
<p>Splitting offensive rebounds across a new roster the way usage is split made every version worse, so offensive rebounding is projected from the player alone. Defensive rebounds are different: when a strong rebounder joins, the others lose some of theirs. For every point of defensive-rebound share his teammates add, a player loses 0.62.</p>
<div class="pair">{sc_reb}</div>
<p class="cap">Per 75 possessions. Offensive: {co_p} of {len(orb)} within 0.5 (last season {co_l}). Defensive: {cd_p} of {len(drb)} within 1.0 (last season {cd_l}).</p>
<h3>The teammate effect, player by player</h3>
<p>Houston added Capela to a frontcourt that already had Şengün and Adams, so the projection cut the defensive rebounding of everyone around them. Where the effect moved a player's projection, the player's actual defensive-rebound share moved the same way {right_d} of {len(shifted)} times.</p>
{ds_tbl}
<div class="pair"><div><p><b>Rebounded more than projected</b></p>{drb_under}</div><div><p><b>Rebounded less</b></p>{drb_over}</div></div>
<h3>2026-27: the random eight</h3>{e6}
</div></section>

<section id="line"><div class="n">7</div><div><h2>Assists, steals, blocks, turnovers</h2>
<p>Each is a rate per 75 possessions from three seasons, then multiplied by projected possessions. The weighting matches how much the stat carries over: assists and blocks lean on last season; steals are noisy, so three seasons count equally; turnovers also move with usage.</p>
<div class="pair four">{sc7}</div>
{t7}
<p class="cap">Players within the close band of their actual '26 rate, last season's rate vs the projection, out of {len(q['ast75'])}. Steals gain the most from pooling.</p>
<h3>Assists follow the role</h3>
<p>Playmaking moved with the job: players handed the ball (Jalen Johnson, Castle, Cam Spencer) beat their projection; scorers who lost touches to a new star or system (Zion, Ingram, Middleton) fell short.</p>
<div class="pair"><div><p><b>More assists than projected</b></p>{ast_under}</div><div><p><b>Fewer</b></p>{ast_over}</div></div>
<h3>2026-27: the random eight</h3>{e7}
</div></section>

<section id="blkd"><div class="n">8</div><div><h2>Own shots blocked</h2>
<p>Every one of a player's shots that gets blocked costs 0.5. Shots at the rim get blocked most (about 10%), then the paint (6%), corner 3s (4%), above-the-break 3s (3%), mid-range almost never. On top of his shot mix, each player has his own rate: catch-and-shoot veterans get blocked about half as often as their shots predict, small drivers about 1.6×.</p>
{fac_tbl}
<p class="cap">Player factor = his blocked shots against what his shot mix predicts, over three seasons, pulled toward 1.0 when the sample is small.</p>
<div class="pair">{sc_bk}</div>
<p class="cap">Projection: {cb_p} of {len(bk)} within 0.15 a game (last season {cb_l}). Typical player about 0.45 a game (−0.23 FP); the most-blocked about 1.3 (−0.65).</p>
<div class="pair"><div><p><b>Blocked more than projected</b></p>{bk_under}</div><div><p><b>Blocked less</b></p>{bk_over}</div></div>
<p>Players whose roles grew got blocked more than their history (Rollins, Alexander-Walker); Cunningham and Zion got blocked less than theirs.</p>
<h3>2026-27: the random eight</h3>{e8}
</div></section>
"""
