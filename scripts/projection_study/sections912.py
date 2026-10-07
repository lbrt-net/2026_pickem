# Sections 9–12, exec'd inside build_report4.py after sections48.py (uses scatter / table / E / f1 / pc / count helpers).
D9 = json.load(open(S + "sec912.json"))
R9 = D9["rows"]
for r in R9:
    r["grp"] = "young" if r["age"] < 24 else ("vet" if r["age"] >= 31 else "prime")
    r["pchg"], r["achg"] = r["proj"] - r["last"], r["act"] - r["last"]
AG = {"young": "g3", "prime": "g1", "vet": "g2"}
akey = '<div class="key"><span><i class="g3"></i>Under 24</span><span><i class="g1"></i>24–30</span><span><i class="g2"></i>31+</span><span><i class="bandkey"></i>within 3 FP</span></div>'
FPH = ["Player", "Age", "'25 FP/G", "Projected '26", "Actual '26"]


def fprow(r, extra=None):
    out = [E(r["name"]), f"{r['age']:.0f}", f1(r["last"]), f"<b>{f1(r['proj'])}</b>", f1(r["act"])]
    return out + ([E(extra)] if extra is not None else [])


def ofn(rows, names):
    by = {r["name"]: r for r in rows}
    return [by[n] for n in names if n in by]


# ---------------- 9. age
young, prime, vet = [[r for r in R9 if r["grp"] == g] for g in ("young", "prime", "vet")]
c9 = {g: (count([dict(proj=r["proj"], act=r["act"]) for r in q], "proj", 3), count([dict(last=r["last"], act=r["act"]) for r in q], "last", 3), len(q))
      for g, q in (("young", young), ("prime", prime), ("vet", vet))}
LAB9 = {"Ryan Rollins", "Reed Sheppard", "Jeremy Sochan", "Kawhi Leonard", "LeBron James", "Stephen Curry", "Zach LaVine", "Donovan Clingan"}
sc9 = scatter(R9, "proj", "act", 0, 45, "projected '26 FP/G", "'26 actual FP/G", LAB9, band=3, groups=AG, title="Projection vs what happened, by age")
sc9c = scatter(R9, "pchg", "achg", -15, 15, "projected change from '25 (FP/G)", "actual change from '25", LAB9, band=3, groups=AG,
               title="Which way the projection moved him vs which way he went")
young_up = table(FPH, [fprow(r) for r in sorted(young, key=lambda r: r["proj"] - r["act"])[:8]])
young_dn = table(FPH, [fprow(r) for r in sorted(young, key=lambda r: r["act"] - r["proj"])[:6]])
vets20 = sorted([r for r in vet if r["last"] >= 20], key=lambda r: r["act"] - r["proj"])
vet_dn = table(FPH, [fprow(r) for r in vets20[:7]])
vet_up = table(FPH, [fprow(r) for r in vets20[::-1][:7]])
age_parts = table(["Where age enters", "What it does"], [
    ["Minutes (section 2)", "career model: next-season minutes by age band, from −0.7 at 22 or younger to −1.5 at 35+, plus years in the league"],
    ["<b>Young minutes (new)</b>", "<b>under 24 in the projected season: +1.5 minutes a game</b>"],
    ["Usage (section 3)", "share of the offense falls with age: −0.4 at 24–27, −1.8 at 31–33"],
    ["Rim and paint (section 4)", "under 24: +1.5 points at the rim, +2 in the paint"]])
young_res = table(["Under 24: actual minus projected (median)", "'24", "'25", "'26 (holdout)"], [
    ["Before: FP/G", "+1.6", "+1.6", "+1.5"], ["Before: minutes", "+1.1", "+2.2", "+0.6"],
    ["<b>With +1.5 minutes: FP/G</b>", "<b>+1.0</b>", "<b>+0.8</b>", "<b>+0.7</b>"], ["All players within 3 FP/G, before → after", "223 → 225", "241 → 246", "229 → 232"]])
EIGHT9 = D9["eight"]
e9 = table(["#", "Player", "Age '27", "'26 FP/G", "PROJ AVG '27", "Age effects in his projection"],
           [[str(i + 1), E(e["name"]), f"{e['age']:.0f}", f1(e["fp26"]) if e["fp26"] else "—", f"<b>{f1(e['fp'])}</b>",
             "young: +1.5 min, rim/paint bump" if e["age"] < 24 else ("veteran: minutes and usage come down" if e["age"] >= 31 else "prime: little age effect")]
            for i, e in enumerate(EIGHT9)])

# ---------------- 10. injuries and the base season
INJ = sorted(D9["injured25"], key=lambda r: -r["proj"])
for r in INJ:
    r["grp"] = "young" if r["age"] < 24 else ("vet" if r["age"] >= 31 else "prime")
inj_tbl = table(["Player", "'25 GP", "Base season", "'25 FP/G", "Projected '26", "Actual '26", "'26 GP"],
                [[E(r["name"]), str(r["gp25"]), f"'{r['base'][2:4]}–{r['base'][-2:]}" if False else f"'{r['base'][-2:]}", f1(r["last"]), f"<b>{f1(r['proj'])}</b>",
                  f1(r["act"]), str(r["gp26"])] for r in INJ[:14]])
base_tbl = table(["Base season needs", "'24 within 3 FP/G", "'25 within 3 FP/G", "'24 + '25"], [
    ["50+ games (old)", "218", "239", "457"], ["40+ games", "220", "244", "464"], ["<b>30+ games (used)</b>", "<b>223</b>", "<b>241</b>", "<b>464</b>"], ["20+ games", "219", "247", "466"]])
_by9 = {r["name"]: r for r in R9}
_old50 = {"Victor Wembanyama": ("'24 (rookie)", "28.4"), "Zion Williamson": ("'24", "27.1"), "Chet Holmgren": ("'24", "24.4"),
          "Jalen Johnson": ("'24", "21.8"), "Kawhi Leonard": ("'24", "26.8"), "Joel Embiid": ("'23 (MVP year)", "34.4")}
base_ex = table(["Player", "'25 GP", "Base with 50+", "Projected", "Base with 30+", "Projected", "Actual '26"],
                [[E(n), str(_by9[n]["gp25"]), o[0], o[1], f"'{_by9[n]['base'][-2:]}", f"<b>{f1(_by9[n]['proj'])}</b>", f1(_by9[n]["act"])]
                 for n, o in _old50.items() if n in _by9])
HURT = sorted(D9["hurt26"], key=lambda r: -r["proj"])
hurt_tbl = table(["Player", "'26 GP", "'25 FP/G", "Projected '26", "Per game when he played"],
                 [[E(r["name"]), str(r["gp26"]), f1(r["last"]), f"<b>{f1(r['proj'])}</b>", f1(r["act"])] for r in HURT])
hurt_held = sum(abs(r["proj"] - r["act"]) <= 3 for r in HURT)
_inj_pts = [dict(name=r["name"], grp="base", proj=r["proj"], act=r["act"]) for r in INJ] + \
           [dict(name=r["name"], grp="hurt", proj=r["proj"], act=r["act"]) for r in HURT if r["name"] not in {x["name"] for x in INJ}]
sc10 = scatter(_inj_pts, "proj", "act", 0, 40, "projected '26 FP/G", "'26 actual FP/G (per game played)",
               {"Victor Wembanyama", "Joel Embiid", "Zion Williamson", "Kawhi Leonard", "Ja Morant", "Jalen Williams", "Brandon Ingram", "Cam Thomas"},
               band=3, groups={"base": "g2", "hurt": "g3"}, title="Injured players: projection vs what happened")
ikey = '<div class="key"><span><i class="g2"></i>Under 30 games in \'25 (older base)</span><span><i class="g3"></i>Under 40 games in \'26</span><span><i class="bandkey"></i>within 3 FP</span></div>'
INJ27 = D9["inj27"]
inj27_tbl = table(["#", "Player", "2026-27", "Base", "'25 FP/G", "'26 FP/G (GP)", "PROJ AVG '27"],
                  [[str(r["rank"]), E(r["name"]), r["team"], f"'{r['base'][-2:]}", f1(r["fp25"]), f"{f1(r['fp26'])} ({r['gp26']})" if r["fp26"] else f"— ({r['gp26']})",
                    f"<b>{f1(r['fp'])}</b>"] for r in INJ27])
e10 = table(["#", "Player", "'25 GP", "'26 GP", "Base", "PROJ AVG '27"],
            [[str(i + 1), E(e["name"]), str(e["gp25"]), str(e["gp26"]), f"'{e['base'][-2:]}", f"<b>{f1(e['fp'])}</b>"] for i, e in enumerate(EIGHT9)])

# ---------------- 11. bad players
lost = sorted([r for r in R9 if r["proj"] - r["act"] >= 4 and r["act"] < 15], key=lambda r: r["act"] - r["proj"])[:12]
lost_tbl = table(["Player", "Age", "'25 MPG", "Projected MPG", "Actual MPG", "Projected FP/G", "Actual FP/G"],
                 [[E(r["name"]), f"{r['age']:.0f}", f1(r["last_mpg"]), f1(r["proj_mpg"]), f1(r["act_mpg"]), f"<b>{f1(r['proj'])}</b>", f1(r["act"])] for r in lost])
_low = [dict(name=r["name"], grp="lost" if r in lost else "other", proj=r["proj_mpg"], act=r["act_mpg"]) for r in R9 if r["last"] < 16]
sc11 = scatter(_low, "proj", "act", 0, 36, "projected '26 minutes", "'26 actual minutes", {r["name"] for r in lost[:6]}, band=3,
               groups={"lost": "g2", "other": "g1"}, title="Players under 16 FP/G in '25: projected vs actual minutes")
ER = sorted([r for r in D9["epm_rows"] if r["mpg"] >= 15], key=lambda r: r["epm"])
epm_tbl = table(["EPM ≤ −2.5, 15+ minutes in '26", "EPM", "'26 MPG", "'26 FP/G"], [[E(r["name"]), f"{r['epm']:.1f}", f1(r["mpg"]), f1(r["fp"])] for r in ER[:12]])
F27 = sorted(D9["flag27"], key=lambda r: r["rank"])
flag_tbl = table(["#", "Player", "2026-27", "'26 EPM", "'26 MPG", "'26 FP/G", "'27 MPG", "PROJ AVG '27"],
                 [[str(r["rank"]), E(r["name"]), r["team"], f"{r['epm']:.1f}", f1(r["mpg26"]), f1(r["fp26"]), f1(r["mpg"]), f"<b>{f1(r['fp'])}</b>"] for r in F27[:14]])
e11 = table(["#", "Player", "'26 EPM", "Flagged?", "PROJ AVG '27"],
            [[str(i + 1), E(e["name"]), f"{e['epm']:.1f}" if e["epm"] == e["epm"] else "above −2.5 (not in the list)", "yes" if e["epm"] == e["epm"] and e["epm"] <= -2.5 else "no",
              f"<b>{f1(e['fp'])}</b>"] for i, e in enumerate(EIGHT9)])

# ---------------- 12. rookies
RK26 = D9["rook26"]
for r in RK26:
    r["grp"] = "young"
LAB12 = {"Cooper Flagg", "VJ Edgecombe", "Kon Knueppel", "Khaman Maluach", "Hansen Yang", "Dylan Harper", "Cedric Coward"}
sc12 = scatter(RK26, "proj", "act", 0, 30, "projected rookie FP/G", "'26 actual FP/G", LAB12, band=3, groups={"young": "g3"}, title="2025 draft class: projection vs what happened")
c12 = count(RK26, "proj", 3)
fb = D9["fits"]["fp"]
coef_tbl = table(["Rookie FP/G", "Effect"], [["Each doubling of the pick number (e.g. #5 → #10)", f"{fb[1] * np.log(2):+.1f}"], ["Each inch of height", f"{fb[2]:+.2f}"],
                                              ["Each 10 lb", f"{fb[3] * 10:+.2f}"], ["Team 10 points a game worse the year before", f"{-10 * fb[4]:+.1f}"]])
top_rk = table(["Pick", "Player", "Team", "Projected", "Actual", "MPG proj → actual"],
               [[f"#{r['pick']}", E(r["name"]), r["team"], f"<b>{f1(r['proj'])}</b>", f1(r["act"]), f"{f1(r['proj_mpg'])} → {f1(r['act_mpg'])}"]
                for r in sorted(RK26, key=lambda r: r["pick"])[:14]])
rk_up = table(["Pick", "Player", "Projected", "Actual"], [[f"#{r['pick']}", E(r["name"]), f"<b>{f1(r['proj'])}</b>", f1(r["act"])] for r in sorted(RK26, key=lambda r: r["proj"] - r["act"])[:6]])
rk_dn = table(["Pick", "Player", "Projected", "Actual"], [[f"#{r['pick']}", E(r["name"]), f"<b>{f1(r['proj'])}</b>", f1(r["act"])] for r in sorted(RK26, key=lambda r: r["act"] - r["proj"])[:6]])
rk_var = table(["Rookie model tried", "Held-out '22–'25 classes within 3 FP/G", "Kept?"], [
    ["<b>Pick, height, weight, team quality</b>", "<b>143 of 259</b>", "<b>Yes</b>"], ["+ a top-3 pick bonus", "141", "No"], ["+ a top-5 pick bonus", "141", "No"],
    ["Top-3 bonus, no height or weight", "137", "No"], ["+ top-3 bonus, 6'10\"+ outside the top 5 marked down", "141", "No"],
    ["Pick, team quality, top-3, 6'10\"+ outside the top 5", "139", "No"]])
rk27 = table(["Pick", "Player", "2026-27", "Height", "Team diff '26", "MPG", "PROJ AVG"],
             [[f"#{r['pick']}", E(r["name"]), r["team"], f"{int(r['height']) // 12}'{int(r['height']) % 12}\"", f"{r['tdiff']:+.1f}", f1(r["mpg"]), f"<b>{f1(r['fp'])}</b>"]
              for r in D9["rook27"][:15]])

sec912_html = f"""
<section id="age"><div class="n">9</div><div><h2>Age and career stage</h2>
<p class="claim">Age changes a player's minutes, his share of the offense and his finishing, and the projection applies it in each of those places. The one place it was short: young players earn minutes faster than the career model gave them.</p>
{age_parts}
<h3>What it looks like on '26</h3>
{akey}
<div class="pair">{sc9}{sc9c}</div>
<p class="cap">Every dot a player with 20+ games in '26, projected from '23–'25 only. Within 3 FP/G of actual: under 24, {c9['young'][0]} of {c9['young'][2]} (last season alone {c9['young'][1]}); 24–30, {c9['prime'][0]} of {c9['prime'][2]} ({c9['prime'][1]}); 31+, {c9['vet'][0]} of {c9['vet'][2]} ({c9['vet'][1]}). Right chart: dots in the top-right and bottom-left went the way the projection moved them.</p>
<h3>Young players: the model was short</h3>
<p>Under-24s beat their projection in every season, the holdout included, and most of it was minutes. So they now get 1.5 more minutes a game, which carries through every stat. What's left is the role jumps nobody can see coming:</p>
{young_res}
<div class="pair"><div><p><b>Outran the projection</b></p>{young_up}</div><div><p><b>Fell short</b></p>{young_dn}</div></div>
<p>Rollins, Tyson and Sheppard went from bench pieces to starters. Sochan, Gradey Dick and Jović lost their spots. That is a coach's decision, and the projection has no way to see it in advance.</p>
<h3>Veterans: some fall off, some don't</h3>
<p>The projection brings a veteran's minutes and usage down a little each year. It splits about evenly: LaVine, Davis and LeBron came down further than projected, while Curry, Durant, Butler and Kawhi held up or rose. Nothing in their history tells the two groups apart, so they get the same treatment.</p>
<div class="pair"><div><p><b>Fell more than projected</b></p>{vet_dn}</div><div><p><b>Held up or rose</b></p>{vet_up}</div></div>
<h3>2026-27: the random eight</h3>{e9}
</div></section>

<section id="injuries"><div class="n">10</div><div><h2>Injuries and the base season</h2>
<p class="claim">Missing games doesn't lower a player's per-game projection. The base season is the most recent one where he played enough to show how he plays now, and 30 games is enough.</p>
<p>The base season sets his minutes and usage starting point. It used to need 50 games, which threw away real seasons: Wembanyama's 46-game '25 didn't count, so his '26 was projected off his rookie year. On the '24 and '25 targets, every cutoff below 50 did better, and 30 games makes basketball sense:</p>
<div class="pair">{base_tbl}{base_ex}</div>
<p class="cap">Embiid is still too high. His base is now '24 (39 games), and his knee took more off him than his history shows.</p>
<h3>Players whose base season isn't last season</h3>
<p>These players played under 30 games in '25, so their base is an older season:</p>
{ikey}
<div class="pair">{sc10}<div>{inj_tbl}</div></div>
<h3>Hurt during the season: per game when he played</h3>
<p>Players who missed most of '26 mostly produced their projection when they did play: {hurt_held} of {len(HURT)} within 3 FP/G. The ones who fell short played hurt or came back diminished: Jalen Williams, Morant, Embiid, LaVine, Ivey.</p>
{hurt_tbl}
<h3>2026-27: players coming off an injured '26</h3>
<p>These are projected per game from their last healthy base season. An Achilles (Haliburton, Tatum, Lillard) can take something off a player even after he's back, and nothing in the projection knows that. Whether he plays at all, and how many games, belongs to the availability model, not here.</p>
{inj27_tbl}
<h3>2026-27: the random eight</h3>{e10}
</div></section>

<section id="bad"><div class="n">11</div><div><h2>Bad players</h2>
<p class="claim">The projection's worst '26 misses were players who lost their role. The coach saw something the box score hadn't yet shown.</p>
<div class="pair">{sc11}<div>{lost_tbl}</div></div>
<p class="cap">Left: every player under 16 FP/G in '25; orange are the twelve biggest '26 misses. Most dots sit on the line. The misses are the ones far below it.</p>
<p>Every one was projected close to his '25 minutes, then lost anywhere from a quarter to more than two-thirds of them. Three rules lean against handing minutes to players who haven't earned them:</p>
<ul><li><b>Short history pulls down only</b> (section 2): under 60 games over three seasons, minutes are pulled toward 16 a game, and never up.</li>
<li><b>Late-season runway is discounted</b> (section 2): minutes picked up in the last fifth of a season, after being benched early, count a tenth.</li>
<li><b>EPM flag</b> (2026-27 only): EPM ≤ −2.5 in '26 cuts minutes until he loses 2.5 FP/G.</li></ul>
<h3>EPM: bad players lose their minutes</h3>
<p>Among players at EPM −2.5 or worse in '26, a worse EPM went with fewer fantasy points (correlation {np.corrcoef([r['epm'] for r in D9['epm_rows']], [r['fp'] for r in D9['epm_rows']])[0, 1]:.2f}). A team that keeps playing a −5 player is usually rebuilding, and that doesn't last. The '26 EPM is a temporary hand-entered list and will be replaced by a pulled stat. Because it is the '26 outcome, it can't be tested on '26.</p>
{epm_tbl}
<h3>2026-27: the flagged players</h3>
{flag_tbl}
<p class="cap">Highest-ranked flagged players. Keegan Murray, Derik Queen, Fears and Ace Bailey are real rotation players with bad '26 impact numbers. Compare their '26 and '27 minutes to see what the flag takes off.</p>
<h3>2026-27: the random eight</h3>{e11}
</div></section>

<section id="rookies"><div class="n">12</div><div><h2>Rookies</h2>
<p class="claim">A rookie has no NBA history, so his projection comes from where he was picked, his size and how bad his new team was. Bad teams play rookies.</p>
<p>The model was fit on the '22–'25 rookie classes ({D9['ntrain']} rookies with 10+ games) and checked on the 2025 class in '26.</p>
{coef_tbl}
<div class="pair">{sc12}<div>{top_rk}</div></div>
<p class="cap">{c12} of {len(RK26)} '26 rookies within 3 FP/G.</p>
<div class="pair"><div><p><b>Beat the projection</b></p>{rk_up}</div><div><p><b>Fell short</b></p>{rk_dn}</div></div>
<p>Flagg, Edgecombe and Knueppel played like no recent top-four picks had: 31–35 minutes and 21–24 FP/G as rookies. Cedric Coward went 11th to a good Memphis team (+4.9 a game the year before) and still played 26 minutes. On the other side, the tall rookies sat: Yang Hansen 7.0 minutes, Beringer 7.9, Maluach 8.9. Fixes for both were tested on held-out past classes. None beat the current model:</p>
{rk_var}
<p class="cap">Each variant was fit four times, leaving out one '22–'25 class each time, then scored on the class it never saw.</p>
<h3>2026-27: the 2026 draft class</h3>
{rk27}
<p class="cap">None of the random eight is a rookie.</p>
</div></section>
"""
