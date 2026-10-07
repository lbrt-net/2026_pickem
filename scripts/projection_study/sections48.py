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

rule_tbl = table(["What was tried for 3P%", "Kept?", "Why"], [
    ["Last season alone", "No", "One season of 3s is mostly luck"],
    ["Pull everyone toward the league average", "No", "Wrong comparison group: drags Curry and Kennard toward non-shooters"],
    ["Pull everyone above 38% halfway (or a quarter) back to 38%", "No", "Treats 2,000 attempts like 200; Curry 40.9 → 39.4 makes no sense"],
    ["Credibility weighting (half weight at ~400 attempts) toward the league", "No", "Still a league complement: Curry −0.6, Kennard 45 → 42"],
    ["Separate caps for corner and above-the-break 3s", "No", "No better; the corner/above-break split is already kept per player"],
    ["Exempt 'proven' shooters (38%+ on 200+ 3PA every one of 3 seasons)", "Folded in", "14 players qualify for '27; the volume rule already leaves them alone"],
    ["<b>Volume is the evidence, both directions</b>", "<b>Yes</b>", "<b>His own 3 seasons; only thin volume gets moved</b>"]])
_ex3 = [("Stephen Curry", 766, 40.9), ("Kevin Durant", 336, 41.7), ("Luke Kennard", 257, 46.0), ("Sam Hauser", 400, 42.0), ("Isaiah Joe", 404, 41.3),
        ("Grayson Allen", 387, 43.1), ("Stephon Castle", 333, 28.5), ("Jock Landale", 50, 28.0), ("Collin Gillespie", 64, 42.2)]
_p3 = {x["name"]: x for x in p3rows}
rule_ex = table(["Player", "3PA / season", "Own 3P%, 3 seasons", "Projected '26", "Actual '26"],
                [[E(n), str(a), f"{o:.1f}%", f"<b>{_p3[n]['proj']:.1f}%</b>", f"{_p3[n]['act']:.1f}%"] for n, a, o in _ex3 if n in _p3])
proven27 = ("Stephen Curry, Kevin Durant, Klay Thompson, Luke Kennard, Sam Hauser, Norman Powell, Jamal Murray, Isaiah Joe, Cameron Johnson, "
            "Collin Sexton, Duncan Robinson, Nickeil Alexander-Walker, Rui Hachimura, Harrison Barnes")
proven_tbl = table(["Proven shooter going into '26", "Own 3P%, 3 seasons", "Actual '26"], [
    ["Luke Kennard", "46.0%", "47.8%"], ["Kevin Durant", "41.7%", "41.3%"], ["Isaiah Joe", "41.3%", "42.4%"], ["Jamal Murray", "40.4%", "43.5%"],
    ["Stephen Curry", "40.9%", "39.3%"], ["Sam Hauser", "42.0%", "39.2%"], ["Grayson Allen", "43.1%", "34.9%"], ["Mike Conley", "41.4%", "33.7%"]])
corner_tbl = table(["Low-volume corner shooter", "3PA / season", "Corner share", "Own 3P%, 3 seasons", "Next season"], [
    ["Patrick Williams ('24)", "148", "41%", "41.4%", "39.9%"], ["Josh Green ('25)", "145", "67%", "38.7%", "39.1%"], ["Aaron Wiggins ('25)", "128", "43%", "39.5%", "38.3%"],
    ["Cason Wallace ('25)", "78", "53%", "41.9%", "35.6%"], ["Cason Wallace ('26)", "147", "50%", "38.9%", "35.1%"]])
# assisted share of 3PM (LeagueDashPlayerStats, Scoring), '21–'26
ast3_tbl = table(["Shooters under 35% over 3 seasons", "Next-season change, test ('24+'25)", "Next-season change, holdout ('26)"], [
    ["95%+ of made 3s assisted", "+3.9 pts", "+2.5 pts"], ["85–95% assisted", "+2.5", "+1.6"], ["Under 85% assisted (more self-created)", "+1.8", "+0.9"]])
ast3_names = table(["Going into '25", "Assisted", "Own 3P%, 3 seasons", "'25"], [
    ["Nikola Vučević", "100%", "32.0%", "40.2%"], ["Ochai Agbaji", "99%", "32.5%", "39.9%"], ["Jaren Jackson Jr.", "96%", "33.0%", "37.5%"], ["P.J. Washington", "95%", "34.2%", "38.1%"],
    ["Pascal Siakam", "92%", "33.7%", "38.9%"], ["De'Aaron Fox", "61%", "34.1%", "31.0%"], ["Ja Morant", "52%", "32.0%", "30.9%"], ["Paolo Banchero", "68%", "32.1%", "32.0%"],
    ["Dejounte Murray", "71%", "34.8%", "29.9%"]])

# ---- 2-point zones: rim, paint, mid
def zrows(i, minatt=100):
    out = []
    for r in RW:
        za, zp = r["act"]["zatt"], r["act"]["zpct"]
        if not za or za[i] < minatt or zp[i] is None or not r["last"]["zpct"] or r["last"]["zpct"][i] is None:
            continue
        out.append(dict(name=r["name"], grp=r["grp"], last=r["last"]["zpct"][i] * 100, proj=r["proj"]["zpct"][i] * 100, act=zp[i] * 100,
                        mpg=r["act"]["mpg"], gp=r["act"]["gp"]))
    return out


ZR = {i: zrows(i) for i in (0, 1, 2)}
ZLAB = {0: {"Rudy Gobert", "Giannis Antetokounmpo", "Ja Morant", "Trae Young", "Stephon Castle", "Zion Williamson"},
        1: {"Shai Gilgeous-Alexander", "Jalen Brunson", "Nikola Jokić", "Anthony Edwards", "Alperen Sengun"},
        2: {"Kevin Durant", "DeMar DeRozan", "Devin Booker", "Shai Gilgeous-Alexander", "Jalen Brunson"}}
ZRNG = {0: (45, 90), 1: (25, 70), 2: (20, 65)}
ZNM = {0: "rim FG%", 1: "paint FG%", 2: "mid-range FG%"}
sc_z = {i: pair_sc(ZR[i], *ZRNG[i], ZNM[i], ZLAB[i], 4, fmt=lambda v: f"{v:.0f}") for i in ZR}
cz = {i: (count(ZR[i], "last", 4), count(ZR[i], "proj", 4), len(ZR[i])) for i in ZR}
zmiss = {i: misses(ZR[i], fmt=lambda v: f"{v:.1f}%") for i in ZR}
zone_tbl = table(["Zone", "League FG%", "One season carries over", "3 seasons carry over", "Attempts for half real skill, half luck"], [
    ["Rim", "about 66%", "0.63", "0.64", "about 70"], ["Paint (not rim)", "about 44%", "0.58", "0.62", "about 100"], ["Mid-range", "about 42%", "0.39", "0.52", "about 180"]])
rim_ht_tbl = table(["What a player's build says about his finishing", "Effect"], [
    ["Each inch of height", "+0.9 pts at the rim"], ["Each 10 pts more of his 2s assisted", "+0.7 pts at the rim"],
    ["Height + assisted share together", "explain 38% of the gap between players at the rim, 5% in the paint"]])
rim_ex = table(["2026-27", "Age", "Rim attempts, 3 seasons", "Own rim FG%", "Projected"], [
    ["Rudy Gobert", "35", "1,363", "74.2%", "<b>74.2%</b>"], ["Giannis Antetokounmpo", "32", "2,004", "76.5%", "<b>76.5%</b>"],
    ["Kevin Durant", "38", "469", "77.6%", "<b>77.6%</b>"], ["Shai Gilgeous-Alexander", "28", "1,238", "70.0%", "<b>70.0%</b>"],
    ["Trae Young", "28", "400", "55.2%", "<b>55.2%</b>"], ["Victor Wembanyama", "23", "989", "73.1%", "<b>74.6%</b>"],
    ["Stephon Castle", "22", "671", "63.3%", "<b>64.8%</b>"], ["Cooper Flagg", "20", "330", "65.8%", "<b>67.3%</b>"]])
paint_ex = table(["2026-27", "Paint attempts a season", "Own paint FG%, 3 seasons", "Projected"], [
    ["Rudy Gobert", "73", "30.1%", "<b>30.1%</b>"], ["Giannis Antetokounmpo", "170", "38.9%", "<b>38.9%</b>"], ["Kevin Durant", "349", "55.0%", "<b>55.0%</b>"],
    ["Shai Gilgeous-Alexander", "395", "51.7%", "<b>51.7%</b>"], ["Ja Morant", "146", "43.5%", "<b>43.5%</b>"], ["Stephon Castle (22)", "129", "36.8%", "<b>39.3%</b>"],
    ["Cooper Flagg (20)", "126", "47.2%", "<b>49.2%</b>"]])
rare_tbl = table(["Zone", "≤6'2\"", "6'3\"–6'5\"", "6'6\"–6'8\"", "6'9\"–6'10\"", "6'11\"+"], [
    ["Rim", "56.0%", "58.1%", "61.3%", "63.8%", "69.0%"], ["Paint", "35.9%", "33.4%", "35.6%", "38.1%", "39.7%"], ["Mid-range", "37.9%", "35.4%", "34.1%", "36.8%", "34.6%"],
    ["Corner 3", "37.2%", "33.4%", "30.7%", "32.5%", "29.3%"], ["Above-the-break 3", "28.5%", "25.6%", "24.9%", "23.5%", "22.9%"]])
mid_win = table(["Mid-range window", "'25 within 4 pts", "'26 within 4 pts"], [["1 season", "33 of 63", "23 of 60"], ["2 seasons", "40 of 64", "28 of 60"],
                                                                             ["3 seasons", "40 of 64", "29 of 60"], ["4 seasons", "39 of 64", "29 of 60"]])
mid_ex = table(["2026-27", "Mid attempts, 5 seasons", "Own mid FG%", "Projected"], [
    ["Kevin Durant", "1,924", "52.7%", "<b>52.7%</b>"], ["DeMar DeRozan", "3,085", "46.2%", "<b>46.2%</b>"], ["Devin Booker", "1,805", "48.4%", "<b>48.4%</b>"],
    ["Shai Gilgeous-Alexander", "1,405", "49.2%", "<b>49.2%</b>"], ["Stephen Curry", "679", "46.2%", "<b>46.2%</b>"], ["Giannis Antetokounmpo", "936", "38.7%", "<b>38.7%</b>"],
    ["Anthony Edwards", "1,083", "37.8%", "<b>37.9%</b>"], ["Josh Hart", "225", "36.4%", "<b>37.1%</b>"], ["Jalen Duren", "74", "35.1%", "<b>35.1%</b>"],
    ["Rudy Gobert", "34", "17.6%", "<b>17.6%</b>"]])
mid_vol = table(["Mid FG%, 3 seasons", "Under 50 att / season", "50–150", "150+"], [
    ["Under 38%", "34.4 → 39.6", "36.2 → 39.8", "36.7 → 40.0"], ["38–45%", "40.4 → 41.7", "41.8 → 42.1", "42.1 → 42.8"], ["45%+", "47.3 → 46.6", "47.3 → 46.5", "47.7 → 46.9"]])
age_tbl = table(["Age in the target season", "Rim: next season vs 3-season rate, test / holdout", "Paint: test / holdout"], [
    ["Under 24", "+1.1 / +2.0", "+2.3 / +2.3"], ["24–29", "+0.2 / +1.2", "+0.7 / +1.0"], ["30–32", "−0.4 / −1.1", "+0.9 / +0.8"], ["33+", "+0.3 / +0.9", "−0.4 / +2.6"]])
ft_win = table(["FT% window", "'25 within 4 pts", "'26 within 4 pts"], [["1 season", "109 of 164", "95 of 188"], ["2 seasons", "111 of 168", "115 of 192"],
                                                                      ["<b>3 seasons</b>", "<b>116 of 168</b>", "<b>120 of 192</b>"], ["4 seasons", "115 of 168", "114 of 192"],
                                                                      ["5 seasons", "— (data starts '21)", "117 of 192"]])
ft_lvl = table(["FT%, 3 seasons", "Under 100 FTA / season", "100–250", "250+"], [
    ["Under 65%", "61.5 → 64.1", "57.5 → 60.9", "—"], ["65–72%", "68.7 → 74.8", "69.1 → 71.8", "68.4 → 67.0"], ["72–80%", "76.0 → 76.7", "76.2 → 77.6", "75.9 → 77.0"],
    ["80–87%", "82.6 → 82.3", "83.9 → 84.1", "84.5 → 84.6"], ["87%+", "88.9 → 84.9", "88.5 → 87.0", "88.9 → 88.2"]])
ft_ht = table(["Height", "FT%, all player-seasons", "FT%, under 30 FTA in the season", "Used for a player with no FT history"], [
    ["6'2\" and under", "84.5%", "77.4%", "<b>69.9%</b>"], ["6'3\"–6'5\"", "80.6%", "75.8%", "<b>68.3%</b>"], ["6'6\"–6'8\"", "77.6%", "73.3%", "<b>65.8%</b>"],
    ["6'9\"–6'10\"", "74.1%", "70.0%", "<b>62.5%</b>"], ["6'11\"+", "72.9%", "66.9%", "<b>59.4%</b>"]])

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
<p class="claim">One rule runs through every make rate below: volume follows skill. A player who is good at a shot takes it often; a player who is bad at it stops taking it. So a bad percentage on low volume is believed and never pulled up (Gobert: 0% from 3, 30% in the paint, 18% from mid-range). A pull up has to be earned by real volume. A good percentage on low volume is tempered, because the evidence is thin. A good percentage on real volume is his own number: elite shooters are never pulled toward anything.</p>
<h3>The shot mix is a player's signature</h3>
<p class="claim">Where a player shoots from barely changes year to year. The misses are players whose role changed.</p>
{mkey}
<div class="pair">{sc_three}<div><p>Share of a player's shots from 3, '25 against '26. The two seasons track almost one for one: {c3_last} of {len(three)} players within 5 points. Weighting the year before (each season counts 5× the one before) changes little: {c3_proj} within 5 points. A trend line was tried and dropped; it chased one-off seasons.</p>
<p>The biggest moves among rotation players: bigs who started shooting 3s (Okongwu, Clingan), guards who took fewer (Jenkins, Pritchard, Melton), and wings who took more (Ja'Kobe Walter):</p>{mix_tbl}</div></div>
<h3>3-point percentage: volume is the evidence</h3>
<p class="claim">One season of 3s tells you little. Three seasons of his own 3s, moved only where the evidence is thin, is the projection. Elite shooters are not pulled toward anything.</p>
<ul><li><b>Below 34%:</b> pulled up toward 34% only as far as his volume earns it. Under 50 attempts a season, not at all: a player who rarely shoots 3s and misses them is a real non-shooter, and teams let him not shoot. At 250+ a season, 70% of the gap: a coach who keeps letting a 31% shooter fire probably knows he's better than that. The pull is full for a spot-up shooter whose 3s are 95%+ assisted and half for a self-creator at 60% or less (below).</li>
<li><b>Above 38%:</b> his own number at 250+ attempts a season. Below that, pulled toward 38% more the thinner the volume (halfway at 50 a season). Curry's 700+ a season is not a sample size question.</li>
<li><b>34–38%:</b> his own number.</li></ul>
<p>Three seasons beat two, four and five. Every other version that was tried, and why it went:</p>
{rule_tbl}
<p>Going into '26, what the rule does by name:</p>
{rule_ex}
<h3>The proven shooters</h3>
<p>38%+ on 200+ attempts in each of the last three seasons. Going into 2026-27 that is 14 players: {proven27}. Most come down about a point the next year; some hold or rise; a few fall off hard. Nothing in their history separates Grayson Allen's 34.9% from Kennard's 47.8%, so they all keep their own number.</p>
{proven_tbl}
<h3>Low-volume corner specialists</h3>
<p>Corner 3s go in at about 39% league-wide, above-the-break at 35%, so a corner specialist at 40%+ is normal. Under 150 attempts a season with 40%+ of them from the corner and 38%+ on 3s, there were only five cases. Two held, Cason Wallace fell off twice. Too few to build a rule on; their corner/above-break split is already kept, so the corner rate counts for what it is.</p>
{corner_tbl}
<h3>Assisted 3s</h3>
<p>The share of a player's made 3s that were assisted carries over from season to season at 0.88: it is a real trait. For good shooters it changes nothing. Mostly-assisted shooters (Hauser, Kennard, Joe) come down the next year by about the same as self-creators (Curry, Brunson, Murray), so "giga assisted" does not explain who holds 40%+.</p>
<p>For bad shooters it matters. A spot-up shooter missing open looks is mostly unlucky; a guy missing his own pull-ups is closer to his level:</p>
<div class="pair">{ast3_tbl}{ast3_names}</div>
<p class="cap">Applied: below 34%, the pull up scales with how assisted his 3s are, from half at 60% assisted or less to full at 95%+. Scottie Barnes (30.7%, 267 a season) goes to 32.7%; Morant (29.0%, 140 a season, self-created) to 29.8%; Fox and Jaren Jackson Jr. sit inside 34–38% and keep their own number.</p>
<div class="pair">{sc_p3}</div>
<p class="cap">Players with 150+ 3-point attempts in '26. Last season alone: {c3p_l} of {n3p} within 3 points (carry-over {corr(p3rows, 'last'):.2f}). Projection: {c3p_p} of {n3p} ({corr(p3rows, 'proj'):.2f}). Three seasons beat two, four and five.</p>
<div class="pair"><div><p><b>Shot better than projected</b></p>{p3_under}</div><div><p><b>Shot worse than projected</b></p>{p3_over}</div></div>
<h3>Two-point zones: rim, paint, mid-range</h3>
<p class="claim">Three different shots with three different make rates. Each one gets its own rule, and it never pulls an elite finisher or mid-range shooter toward the league.</p>
<p>How much each zone carries over, and how many attempts it takes before a player's rate is more skill than luck:</p>
{zone_tbl}
<h3>Rim: height and assisted share</h3>
<p>Size and getting fed at the rim explain a lot of finishing: taller players and players whose 2s are set up by teammates finish better. The rim projection is his own three-season rate. Only a small sample (under 100 rim attempts) that looks better than what players his height and assisted share finish at is tempered toward that, with his own makes counting half at 20 attempts. A finisher below that line keeps his own number. Players under 24 add 1.5 points (below).</p>
<div class="pair">{rim_ht_tbl}{rim_ex}</div>
<div class="pair">{sc_z[0]}</div>
<p class="cap">Players with 100+ rim attempts in '26. Last season: {cz[0][0]} of {cz[0][2]} within 4 points. Projection: {cz[0][1]} of {cz[0][2]}.</p>
<div class="pair"><div><p><b>Finished better than projected</b></p>{zmiss[0][0]}</div><div><p><b>Finished worse</b></p>{zmiss[0][1]}</div></div>
<h3>Paint (not rim): touch, not size</h3>
<p>Height and assisted share were the obvious guess for the paint too. They explain only 5% of the gap between players there: floaters, hooks and runners are touch. The paint is his own three-season rate. Below 38% it is pulled up only as far as real volume earns it: none under 100 paint shots a season, 65% of the gap at 250+. Gobert takes 73 a season at 30%: he has no touch there, and the projection says so.</p>
{paint_ex}
<div class="pair">{sc_z[1]}</div>
<p class="cap">Players with 100+ paint attempts in '26. Last season: {cz[1][0]} of {cz[1][2]} within 4 points. Projection: {cz[1][1]} of {cz[1][2]}.</p>
<div class="pair"><div><p><b>Shot better than projected</b></p>{zmiss[1][0]}</div><div><p><b>Shot worse</b></p>{zmiss[1][1]}</div></div>
<h3>Young players get better at the rim and in the paint</h3>
<p>Players under 24 beat their three-season rate the next year at the rim and in the paint, in the test seasons and the '26 holdout alike. Applied: under 24 in the projected season, +1.5 points at the rim and +2 in the paint (Wembanyama, Castle, Flagg above).</p>
{age_tbl}
<h3>Mid-range: a long window and a bracket</h3>
<p>Mid-range is the least wanted shot in the regular-season game, so few players take many. One season of it is mostly luck (carry-over 0.39); more seasons help:</p>
<div class="pair">{mid_win}{mid_vol}</div>
<p>So the evidence is a five-season average, with a bracket on top like 3s:</p>
<ul><li><b>38–45%:</b> his own number.</li>
<li><b>Below 38%:</b> pulled up toward 38% only as far as his volume earns it: none at 100 or fewer mid-range attempts over the five seasons, 65% of the gap at 300+. A guy who rarely takes it and misses has no touch; a coach who keeps letting him take it knows something.</li>
<li><b>Above 45%:</b> his own number at 300+ attempts over five seasons; pulled toward 45% only on thin evidence (halfway at 100 or fewer).</li></ul>
{mid_ex}
<div class="pair">{sc_z[2]}</div>
<p class="cap">Players with 100+ mid-range attempts in '26. Last season: {cz[2][0]} of {cz[2][2]} within 4 points. Projection: {cz[2][1]} of {cz[2][2]}.</p>
<div class="pair"><div><p><b>Shot better than projected</b></p>{zmiss[2][0]}</div><div><p><b>Shot worse</b></p>{zmiss[2][1]}</div></div>
<h3>Small samples and shots he never takes</h3>
<p>The comparison group for a small sample is players like him, never the league: what players his height shoot from a zone they rarely use (1–19 attempts in a season, '21–'25).</p>
{rare_tbl}
<ul><li><b>A small sample that looks good</b> (under 100 attempts in the window, above that line) is tempered toward it, his own makes counting half at 20 attempts. A 2-for-2 from mid-range is not a 100% shooter.</li>
<li><b>A small sample that looks bad</b> is believed. Gobert's 0-for-8 from 3 projects 0%.</li>
<li><b>A zone he never shot from</b> in the window gets that line minus 7.5 points, the same as free throws: he is an unknown there, and his share of shots there is near zero anyway.</li></ul>
<p>Overall FG% follows from the zone mix, so when a player's shots move, his FG% moves with them: {cfg_p} of {len(fgp)} within 3 points of actual FG%, against {cfg_l} for last season's FG%.</p>
<h3>Shot volume</h3>
<div class="pair">{sc_fga}<div><p>Shots per 75 possessions, with the usage adjustment from section 3: {cfa_p} of {len(fga)} within 1.5 shots, against {cfa_l} for last season's rate. The misses are players who got a bigger or smaller role after a move or an injury next to them.</p></div></div>
<div class="pair"><div><p><b>Shot more than projected</b></p>{fga_under}</div><div><p><b>Shot less than projected</b></p>{fga_over}</div></div>
<p class="cap">Named lists show rotation players (20+ minutes, 40+ games) so a few games of a fringe player don't crowd them out.</p>
<h3>2026-27: the random eight</h3>{e4}
</div></section>

<section id="ft"><div class="n">5</div><div><h2>Free throws</h2>
<p>Free-throw attempts per 75 possessions come from three seasons weighted toward the latest, scaled by usage. FT% is his own makes over attempts across three seasons, with no pull toward anything.</p>
<h3>Getting to the line</h3>
<div class="pair">{sc_fta}<div><p>{cft_p} of {len(fta)} within one attempt per 75, against {cft_l} for last season's rate. The players who got to the line far more than projected were taking on bigger roles: Avdija, Duren, Wembanyama, Jaylen Brown.</p></div></div>
<div class="pair"><div><p><b>Got to the line more</b></p>{fta_under}</div><div><p><b>Got there less</b></p>{fta_over}</div></div>
<h3>FT% is a skill, but one season is a small sample</h3>
<p class="claim">Three seasons of his own free throws, nothing else. Good free-throw shooters hold their number at any volume.</p>
<p>Three seasons against five: three is at least as good. FT% can move with development, and five seasons lag behind it.</p>
<div class="pair">{ft_win}{ft_lvl}</div>
<p class="cap">Left: within 4 points of actual FT%, 100+ FTA in the target season. Right: three-season FT% → next season, attempt-weighted, by level and volume. 80%+ shooters hold at every volume; bad free-throw shooters who live at the line stay bad (68.4 → 67.0); low-volume bad ones bounce back. No pull was kept: the bounce is in small samples, and the projection doesn't move anyone on a guess.</p>
<h3>A player with no free-throw history</h3>
<p>Not the league average and not zero. FT% falls with height, and players who rarely get to the line shoot worse than those who live there. A player with no free throws in three seasons gets what rarely-fouled players his height shoot, minus 7.5 points because he is an unknown:</p>
{ft_ht}
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
