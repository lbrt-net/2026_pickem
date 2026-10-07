"""Report v4: sections 1–3 as player-level analysis (no average-error tables); 4–17 outline."""
import csv, html, json
import numpy as np
S = "/private/tmp/claude-501/-Users-allan-PycharmProjects-2026-pickem/42c9de93-ee73-4708-9f07-f8fdb3ea7c56/scratchpad/"
Z = json.load(open(S + "sec23c.json"))
Y = json.load(open(S + "sec23b.json"))
B = json.load(open(S + "board.json"))
E = html.escape
f1 = lambda v: "—" if v is None or v != v else f"{v:.1f}"  # noqa: E731
pc = lambda v: "—" if v is None or v != v else f"{v * 100:.1f}%"  # noqa: E731
PROJ = {r["name"]: r for r in csv.DictReader(open("/Users/allan/PycharmProjects/nba-pipeline/data/raw/projections_2026_27.csv"))}

M = [r for r in Z["mins"] if r["last"] is not None and r["final"] is not None]
for r in M:
    r["grp"] = "moved" if "new team" in r["why"] else ("short" if "GP in" in r["why"] else "stable")
GC = {"stable": "g1", "moved": "g2", "short": "g3"}
GL = {"stable": "Same team, full seasons", "moved": "Changed teams", "short": "Short season ('25 or '26 under 40 games)"}


def table(head, rows, cls="r"):
    return (f'<div class="tw"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</tbody></table></div>")


def scatter(rows, xkey, ykey, lo, hi, xlab, ylab, labels, band=3, groups=GC, fmt=f1, w=440, title=""):
    l, r, t, b = 46, 14, 26, 44
    h = w
    X = lambda v: l + (v - lo) / (hi - lo) * (w - l - r)  # noqa: E731
    Yp = lambda v: t + (hi - v) / (hi - lo) * (h - t - b)  # noqa: E731
    o = [f'<text class="mt" x="{l}" y="14">{E(title)}</text>'] if title else []
    step = 10 if hi - lo > 30 else 5
    v = lo
    while v <= hi + 1e-9:
        o.append(f'<line class="grid" x1="{l}" x2="{w - r}" y1="{Yp(v):.1f}" y2="{Yp(v):.1f}"/><line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{t}" y2="{h - b}"/>'
                 f'<text class="ax" x="{l - 6}" y="{Yp(v) + 4:.1f}" text-anchor="end">{fmt(v) if step < 1 else int(v) if v == int(v) else v}</text>'
                 f'<text class="ax" x="{X(v):.1f}" y="{h - b + 15}" text-anchor="middle">{fmt(v) if step < 1 else int(v) if v == int(v) else v}</text>')
        v += step
    if band:
        o.append(f'<polygon class="band" points="{X(lo):.1f},{Yp(lo + band):.1f} {X(hi - band):.1f},{Yp(hi):.1f} {X(hi):.1f},{Yp(hi):.1f} {X(hi):.1f},{Yp(hi - band):.1f} {X(lo + band):.1f},{Yp(lo):.1f} {X(lo):.1f},{Yp(lo):.1f}"/>')
    o.append(f'<line class="diag" x1="{X(lo):.1f}" y1="{Yp(lo):.1f}" x2="{X(hi):.1f}" y2="{Yp(hi):.1f}"/>')
    o.append(f'<text class="ax" x="{(l + w - r) / 2:.1f}" y="{h - 8}" text-anchor="middle">{E(xlab)}</text>'
             f'<text class="ax" x="12" y="{(t + h - b) / 2:.1f}" transform="rotate(-90 12 {(t + h - b) / 2:.1f})" text-anchor="middle">{E(ylab)}</text>')
    for p in rows:
        xv, yv = p[xkey], p[ykey]
        if xv is None or yv is None:
            continue
        xv, yv = min(max(xv, lo), hi), min(max(yv, lo), hi)
        o.append(f'<circle class="pt {groups.get(p.get("grp"), "g1")}" cx="{X(xv):.1f}" cy="{Yp(yv):.1f}" r="3.6"><title>{E(p["name"])}: {fmt(p[xkey])} → {fmt(p[ykey])}</title></circle>')
    for p in rows:
        if p["name"] in labels and p[xkey] is not None:
            xv, yv = min(max(p[xkey], lo), hi), min(max(p[ykey], lo), hi)
            anchor = "end" if X(xv) > w * 0.7 else "start"
            dx = -7 if anchor == "end" else 7
            o.append(f'<text class="pl" x="{X(xv) + dx:.1f}" y="{Yp(yv) + 4:.1f}" text-anchor="{anchor}">{E(p["name"].split()[-1] if p["name"].split()[-1] not in ("Jr.", "III") else p["name"].split()[-2])}</text>')
    return f'<svg class="sc" viewBox="0 0 {w} {h}" role="img" aria-label="{E(title or ylab)}">{"".join(o)}</svg>'


def within(rows, key, band=3):
    ok = [r for r in rows if r[key] is not None]
    return sum(abs(r[key] - r["act"]) <= band for r in ok), len(ok)


key_groups = '<div class="key">' + "".join(f'<span><i class="{c}"></i>{E(GL[g])}</span>' for g, c in GC.items()) + \
             '<span><i class="bandkey"></i>within 3 minutes</span></div>'

# ---------------- section 2 numbers
stars = sorted([r for r in M if r["act"] >= 33], key=lambda r: -r["act"])
st_last, st_n = within(stars, "last")
st_flat, _ = within(stars, "flat")
st_fin, _ = within(stars, "final")
moved2 = [r for r in M if abs(r["final"] - r["last"]) >= 2]
right = sum((r["final"] - r["last"]) * (r["act"] - r["last"]) > 0 for r in moved2)
sd = lambda k: float(np.std([r[k] for r in M], ddof=1))  # noqa: E731
grp_counts = {g: within([r for r in M if r["grp"] == g], "last") for g in GC}
stable_st = [r for r in M if r["grp"] == "stable" and r["last"] >= 28]
over = sorted([r for r in stable_st if r["final"] - r["act"] > 3], key=lambda r: r["act"] - r["final"])
under = sorted([r for r in stable_st if r["final"] - r["act"] < -3], key=lambda r: r["final"] - r["act"])
good_st = sorted([r for r in stable_st if abs(r["final"] - r["act"]) <= 1.5], key=lambda r: -r["act"])
allerr = sorted(M, key=lambda r: r["final"] - r["act"])
LAB1 = {"Ryan Rollins", "Jonathan Mogbo", "Jeremy Sochan", "Kevin Porter Jr.", "Jaylon Tyson", "Nikola Jokić", "Anthony Edwards", "Gradey Dick"}
sc_last = scatter(M, "last", "act", 0, 42, "'25 minutes per game", "'26 actual minutes per game", LAB1, title="Last season's minutes vs what happened")
sc_flat = scatter(M, "flat", "act", 0, 42, "projected with a flat pull toward 26.9", "'26 actual", LAB1, title="Flat pull toward the middle")
sc_fin = scatter(M, "final", "act", 0, 42, "final projection", "'26 actual", LAB1, title="Final model vs what happened")


def mrow(r, extra=""):
    return [E(r["name"]), f1(r["last"]), f"<b>{f1(r['final'])}</b>", f1(r["act"]), f"{r['final'] - r['act']:+.1f}", f'<span class=dim>{E(extra or r["why"])}</span>']


MH = ["Player", "'25 MPG", "Projected '26", "Actual '26", "Off by", "Notes"]
fix_rows = [mrow(r) for r in M if r["name"] in ("Kevin McCullar Jr.", "Pacôme Dadiet", "Xavier Tillman")]
works = table(MH, [mrow(r, "") for r in good_st[:12]])
vets_down = table(MH, [mrow(r, "") for r in over])
young_up = table(MH, [mrow(r, "") for r in under])
role = table(MH, [mrow(r) for r in allerr[:8]] + [mrow(r) for r in allerr[::-1][:8]])
star_tbl = table(["Player", "'25 MPG", "Flat pull", "Final", "Actual '26"],
                 [[E(r["name"]), f1(r["last"]), f1(r["flat"]), f"<b>{f1(r['final'])}</b>", f1(r["act"])] for r in stars[:15]])
grid = table(["Prior MPG ↓ / usage →", "under 16%", "16–20%", "20–24%", "24–28%", "28%+"], [
    ["Under 16", "+2.3", "+3.1", "+2.6", "+2.4", "+2.4"], ["16–22", "−0.2", "−1.5", "−0.8", "−0.1", "—"],
    ["22–28", "−2.2", "−1.2", "−1.3", "−1.3", "−1.3"], ["28–32", "−2.4", "−1.8", "−1.3", "−0.9", "−0.6"],
    ["32–35", "−0.9", "−1.1", "−1.3", "−0.8", "<b>+0.1</b>"], ["35+", "—", "−1.1", "−1.0", "−1.0", "<b>−0.7</b>"]])
ages = table(["Age", "≤22", "23–25", "26–28", "29–31", "32–34", "35+"], [["Next-season minutes", "−0.7", "−0.4", "0.0", "−1.3", "−1.1", "−1.5"]])
tank = table(["Team point differential where he earned the minutes", "Next-season change", "If he changed teams"],
             [["Tank (−8 or worse per game)", "−2.5", "−4.4"], ["−8 to −4", "−2.7", "−4.5"], ["−4 to 0", "−1.6", "−3.9"],
              ["0 to +4", "−1.0", "−2.3"], ["+4 or better", "+0.2", "−1.1"]])
pace_tbl = table(["Player", "Projected pace", "Actual pace", "Projected MIN", "Actual MIN", "Projected poss/G", "Actual poss/G"],
                 [[E(r["name"]), f1(r["own"]), f1(r["act"]), f1(r["mpg"]), f1(r["act_mpg"]), f"<b>{f1(r['poss'])}</b>", f1(r["act_poss"])] for r in Y["pace_rows"]])
s27 = Y["sample27"]
wrap2 = table(["#", "Player", "Team", "'26 MPG (GP)", "'27 MPG", "'27 poss/G", "Why it moved"],
              [[str(r["rank"]), E(r["name"]), r["team"], f"{f1(r['mpg26'])} <span class=dim>({r['gp26']})</span>", f"<b>{f1(r['mpg'])}</b>", f1(r["poss"]),
                '<span class=dim>' + E(", ".join(x for x in [("age " + str(int(r["age"]))) if r["age"] >= 31 else "", "new team" if not r["stayed"] else "",
                                                          f"based on '{r['base'][-2:]}" if r["base"] != "2025-26" else ""] if x)) + "</span>"] for r in s27])

# ---------------- section 3 (usage)
UZ = Z["usage"]
for r in UZ:
    r["grp"] = "moved" if r["moved"] else "stable"
stay = [r for r in UZ if not r["moved"]]
mov = [r for r in UZ if r["moved"]]
w15 = lambda rows, k: (sum(abs(r[k] - r["act"]) <= 0.015 for r in rows), len(rows))  # noqa: E731
s_last, s_n = w15(stay, "u0")
s_rs, _ = w15(stay, "resplit")
m_last, m_n = w15(mov, "u0")
m_rs, _ = w15(mov, "resplit")
for r in UZ:
    r["u0p"], r["actp"], r["finp"], r["rsp"] = r["u0"] * 100, r["act"] * 100, r["final"] * 100, r["resplit"] * 100
ULAB = {"Nickeil Alexander-Walker", "Kevin Durant", "Jalen Brunson", "Desmond Bane", "Myles Turner", "Anthony Edwards"}
sc_u0 = scatter(UZ, "u0p", "actp", 8, 38, "'25 usage %", "'26 actual usage %", ULAB, band=1.5, groups={"stable": "g1", "moved": "g2"},
                fmt=lambda v: f"{v:.0f}", title="Last season's usage vs what happened")
sc_uf = scatter(UZ, "finp", "actp", 8, 38, "final projection, usage %", "'26 actual usage %", ULAB, band=1.5, groups={"stable": "g1", "moved": "g2"},
                fmt=lambda v: f"{v:.0f}", title="Final rule vs what happened")
ukey = '<div class="key"><span><i class="g1"></i>Same team</span><span><i class="g2"></i>Changed teams</span><span><i class="bandkey"></i>within 1.5 points</span></div>'
st_moves = sorted(stay, key=lambda r: -abs(r["resplit"] - r["u0"]))[:10]
rs_tbl = table(["Player", "Team", "'25 USG", "Re-split '26", "Actual '26", "Re-split moved it the right way?"],
               [[E(r["name"]), r["t1"], pc(r["u0"]), f"<b>{pc(r['resplit'])}</b>", pc(r["act"]),
                 "yes" if (r["resplit"] - r["u0"]) * (r["act"] - r["u0"]) > 0 else "no"] for r in st_moves])
mv_tbl = table(["Player", "Move", "'25 USG", "Re-split would say", "Actual '26", "Kept his own (final)"],
               [[E(r["name"]), f'{r["t0"]} → {r["t1"]}', pc(r["u0"]), pc(r["resplit"]), f"<b>{pc(r['act'])}</b>", pc(r["u0"])] for r in sorted(mov, key=lambda r: -r["u0"])])
rs_right = sum((r["resplit"] - r["u0"]) * (r["act"] - r["u0"]) > 0 for r in stay if abs(r["resplit"] - r["u0"]) >= 0.01)
rs_n = sum(abs(r["resplit"] - r["u0"]) >= 0.01 for r in stay)
wrap3 = table(["#", "Player", "Team", "'26 USG", "'27 USG", "How"],
              [[str(r["rank"]), E(r["name"]), r["team"], pc(r["usg26"]), f"<b>{pc(r['usg'])}</b>",
                f"re-split on the 2026-27 roster (base '{r['base'][-2:]})" if r["stayed"] else "changed teams: keeps his own"] for r in s27])

# ---------------- usage: age / level / efficiency (usage2.py)
import pandas as pd


def hbars(rows, lo, hi, label, tick=0.5, w=560, lw=170):
    rw, rh, t = 56, 28, 6
    H = t + rh * len(rows) + 24
    Xs = lambda v: lw + (v - lo) / (hi - lo) * (w - lw - rw)  # noqa: E731
    o = []
    v = lo
    while v <= hi + 1e-9:
        o.append(f'<line class="grid" x1="{Xs(v):.1f}" x2="{Xs(v):.1f}" y1="{t}" y2="{t + rh * len(rows)}"/><text class="ax" x="{Xs(v):.1f}" y="{t + rh * len(rows) + 15}" text-anchor="middle">{v:+g}</text>')
        v += tick
    o.append(f'<line class="diag" x1="{Xs(0):.1f}" x2="{Xs(0):.1f}" y1="{t}" y2="{t + rh * len(rows)}" style="stroke-dasharray:none"/>')
    for i, (name, val) in enumerate(rows):
        y = t + i * rh + 5
        x0, x1 = sorted([Xs(0), Xs(val)])
        o.append(f'<text class="pl" x="{lw - 8}" y="{y + 12}" text-anchor="end" style="font-weight:400">{E(name)}</text>'
                 f'<rect class="g1" x="{x0:.1f}" y="{y}" width="{max(x1 - x0, 1.5):.1f}" height="17" rx="3"><title>{E(name)}: {val:+.2f} usage points</title></rect>'
                 f'<text class="ax" x="{Xs(val) + (6 if val >= 0 else -6):.1f}" y="{y + 12}" text-anchor="{"start" if val >= 0 else "end"}">{val:+.1f}</text>')
    return f'<svg class="sc" viewBox="0 0 {w} {H}" role="img" aria-label="{E(label)}">{"".join(o)}</svg>'


age_bars = hbars([("23 or younger", -0.05), ("24–27", -0.42), ("28–30", -0.50), ("31–33", -1.76), ("34+", -1.07)], -2, 0.5, "Usage change by age")
ts_bars = hbars([("TS% bottom quarter", -0.78), ("2nd quarter", -0.56), ("3rd quarter", 0.07), ("TS% top quarter", -0.56)], -2, 0.5, "Usage change by efficiency")
U26 = pd.read_pickle(S + "usage26_check.pkl")
U26["d"] = U26.new - U26.base
for c in ["base", "new", "act"]:
    U26[c + "p"] = U26[c] * 100
U26["grp"] = np.where(U26.moved, "moved", "stable")
n_old = int((abs(U26.base - U26.act) <= 0.015).sum())
n_new = int((abs(U26.new - U26.act) <= 0.015).sum())
adj_rows = [[E(r.name), f"{r.age:.0f}", "moved" if r.moved else "stayed", pc(r.u0), pc(r.base), f"<b>{pc(r.new)}</b>", pc(r.act),
             "yes" if (r.new - r.base) * (r.act - r.base) > 0 else "no"] for r in U26.sort_values("d").head(8).itertuples()]
adj_tbl = table(["Player", "Age", "", "'25 USG", "Before", "With age + level", "Actual '26", "Right way?"], adj_rows)
sc_unew = scatter(U26.to_dict("records"), "newp", "actp", 8, 38, "final projection, usage %", "'26 actual usage %",
                  {"Kevin Durant", "LeBron James", "Shai Gilgeous-Alexander", "Nickeil Alexander-Walker", "Pascal Siakam", "Jalen Brunson"},
                  band=1.5, groups={"stable": "g1", "moved": "g2"}, fmt=lambda v: f"{v:.0f}", title="Final rule vs what happened")
old_stars = table(["Player", "2026-27", "Age", "Base usage", "Re-split / own", "With age + level"], [
    ["Anthony Davis", "WAS (moved)", "34", "30.1% ('25)", "30.1%", "<b>25.9%</b>"], ["LeBron James", "PHI (moved)", "42", "26.2%", "26.2%", "<b>23.9%</b>"],
    ["Kevin Durant", "HOU", "38", "26.3%", "28.0%", "<b>26.4%</b>"], ["Stephen Curry", "GSW", "39", "28.6% ('25)", "29.9%", "<b>28.0%</b>"],
    ["Jalen Brunson", "NYK", "30", "29.6%", "32.4%", "<b>30.8%</b>"], ["Jayson Tatum", "BOS", "29", "30.1% ('25)", "33.9%", "<b>32.3%</b>"]])

# ---------------- summary
top10 = table(["#", "Player", "Team", "Pos", "PROJ AVG", "Middle 50%", "Flags"],
              [[str(i + 1), E(x["name"]), x["team"], x["pos"], f"<b>{x['fp']:.1f}</b>", f"{x['lo']:.1f}–{x['hi']:.1f}", E(x["flags"] or "")] for i, x in enumerate(B[:10])])
wrap1 = table(["#", "Player", "Team", "Pos", "Age", "PROJ AVG", "Middle 50%", "Flags"],
              [[str(r["rank"]), E(r["name"]), r["team"], PROJ[r["name"]]["pos"], f"{r['age']:.0f}", f"<b>{float(PROJ[r['name']]['fp']):.1f}</b>",
                f"{float(PROJ[r['name']]['lo']):.1f}–{float(PROJ[r['name']]['hi']):.1f}", E(PROJ[r["name"]]["flags"] or "")] for r in s27])

exec(open(S + "sections48.py").read())
exec(open(S + "sections912.py").read())
OUTLINE = [
    ("13", "Positions", ["Role-based G / F / C and slot values"]),
    ("14", "Uncertainty", ["Ranges by group; dispersion against usage, minutes and player quality"]),
    ("15", "Player cards", ["Per player: past seasons, projection, actual"]),
    ("16", "2026-27 board", ["Top 50 with last three seasons"]),
    ("17", "Open problems", []),
]
outline = "".join(f'<section class="todo"><div class="n">{n}</div><div><h2>{E(t)} <span class="tag">outline</span></h2><ul>'
                  + "".join(f"<li>{E(i)}</li>" for i in items) + "</ul></div></section>" for n, t, items in OUTLINE)

page = f"""<title>Per-Game Fantasy Projections</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..100,500..800&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: numbered sections; claims backed by player scatter plots (every dot a player) and named tables. */
:root {{
  --bg:#f6f7f9; --panel:#ffffff; --ink:#151a21; --ink-2:#4b5361; --rule:#d8dce3; --grid:#e8ebef; --accent:#2a78d6;
  --g1:#2a78d6; --g2:#eb6834; --g3:#1baf7a; --band:rgba(42,120,214,.09);
  --display:"Archivo","Arial Narrow",Arial,sans-serif; --body:"IBM Plex Sans",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg:#111418; --panel:#181c21; --ink:#eef1f5; --ink-2:#a8b0bc; --rule:#2b3139; --grid:#22282e; --accent:#3987e5;
  --g1:#3987e5; --g2:#d95926; --g3:#199e70; --band:rgba(57,135,229,.14); color-scheme:dark }} }}
:root[data-theme="dark"] {{ --bg:#111418; --panel:#181c21; --ink:#eef1f5; --ink-2:#a8b0bc; --rule:#2b3139; --grid:#22282e; --accent:#3987e5;
  --g1:#3987e5; --g2:#d95926; --g3:#199e70; --band:rgba(57,135,229,.14); color-scheme:dark }}
body {{ background:var(--bg); color:var(--ink); font:15.5px/1.6 var(--body); }}
.wrap {{ max-width:960px; margin:0 auto; padding-inline:20px; padding-block:40px 80px; }}
.eyebrow {{ font:600 12px/1 var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--ink-2); }}
h1 {{ font-family:var(--display); font-stretch:72%; font-weight:800; font-size:clamp(32px,6vw,48px); line-height:1.02; margin:.35em 0 .3em; }}
section {{ border-top:1px solid var(--rule); padding-block:22px 10px; display:grid; grid-template-columns:44px 1fr; gap:4px 14px; }}
section > .n {{ font:600 14px/1.8 var(--mono); color:var(--accent); }} section > div {{ min-width:0; }}
h2 {{ font-family:var(--display); font-stretch:85%; font-weight:750; font-size:28px; margin:0 0 8px; display:flex; gap:10px; align-items:center; flex-wrap:wrap; }}
h3 {{ font-family:var(--display); font-stretch:90%; font-weight:650; font-size:19px; margin:26px 0 4px; }}
p, li {{ max-width:72ch; }}
.claim {{ font-weight:600; }}
.formula {{ font-family:var(--mono); font-size:14px; background:var(--panel); border:1px solid var(--rule); border-radius:6px; padding:8px 12px; display:inline-block; }}
.pair.four {{ grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); }}
.pair {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:14px 22px; margin:10px 0; }}
.pair > * {{ min-width:0; }}
.sc {{ width:100%; height:auto; font-family:var(--body); }}
.mt {{ fill:var(--ink); font-size:13px; font-weight:600; }}
.grid {{ stroke:var(--grid); }} .diag {{ stroke:var(--ink-2); stroke-dasharray:4 4; }} .band {{ fill:var(--band); }}
.ax {{ fill:var(--ink-2); font-size:11px; }} .pl {{ fill:var(--ink); font-size:11px; font-weight:600; }}
.pt {{ stroke:var(--panel); stroke-width:1; fill-opacity:.85; }} .pt:hover {{ fill-opacity:1; stroke:var(--ink); }}
.g1 {{ fill:var(--g1); }} .g2 {{ fill:var(--g2); }} .g3 {{ fill:var(--g3); }}
.key {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; color:var(--ink-2); }}
.key i {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; vertical-align:-1px; }}
.key i.g1 {{ background:var(--g1); }} .key i.g2 {{ background:var(--g2); }} .key i.g3 {{ background:var(--g3); }} .key i.bandkey {{ background:var(--band); border-radius:2px; border:1px solid var(--rule); }}
.tw {{ overflow-x:auto; margin:10px 0 4px; border:1px solid var(--rule); border-radius:6px; background:var(--panel); }}
table {{ border-collapse:collapse; width:100%; font-size:13.5px; }}
th, td {{ padding:6px 10px; border-bottom:1px solid var(--rule); white-space:nowrap; font-variant-numeric:tabular-nums; text-align:left; }}
table.r td:not(:first-child), table.r th:not(:first-child) {{ text-align:right; }}
table.r td:last-child {{ text-align:left; white-space:normal; }}
th {{ font:600 11px/1.3 var(--mono); text-transform:uppercase; letter-spacing:.04em; color:var(--ink-2); }}
tbody tr:last-child td {{ border-bottom:0; }}
.dim {{ color:var(--ink-2); }} .cap {{ font-size:13px; color:var(--ink-2); margin:2px 0 14px; }}
.tag {{ font:500 11px/1 var(--mono); padding:4px 6px; border-radius:4px; border:1px solid var(--rule); color:var(--ink-2); }}
section.todo ul {{ color:var(--ink-2); padding-left:18px; margin:0; }}
@media (max-width:520px) {{ section {{ grid-template-columns:1fr; }} }}
</style>
<div class="wrap">
<div class="eyebrow">Fantasy 2026-27 · Per-game projection (PROJ AVG)</div>
<h1>Per-game fantasy projections</h1>
<p class="dim">Sections 1–12 written; 13–17 to come. Seasons are named by the year they end ('26 = 2025-26). Every '26 projection shown was made from '23–'25 only, then checked against what happened.</p>

<section id="summary"><div class="n">1</div><div><h2>Summary</h2>
<p><b>PROJ AVG</b> is what a player should score in a game he plays, under the league's scoring. It is built the way a stat line is: minutes, possessions, his share of the offense, where his shots come from and how often they go in, free throws, rebounds, assists, steals, blocks, turnovers. Games missed and best-game-of-the-week (PROJ MAX) are separate.</p>
<p>The test for every piece is player by player: what we projected for '26 against what happened, who it gets right, who it gets wrong and why. A projection that is close on average but squeezes stars down and bench players up is wrong for a draft board, and gets rejected even when it looks better on paper.</p>
<p><b>What holds up:</b> minutes for established starters on the same team (mostly by carrying last season forward); adjustments for age, short histories and tank-team minutes, which move projections the right way 84% of the time when they move them; the usage re-split for players who stayed, modestly. <b>What doesn't yet:</b> players whose role changes (Rollins up, Mogbo down), veterans losing minutes faster than expected (Booker, Fox, Bridges), young players taking bigger roles (Amen Thompson, Keyonte George), and players who change teams.</p>
<h3>2026-27 top 10</h3>
{top10}
<h3>2026-27: random players from the top 125</h3>
{wrap1}
<p class="cap">These eight close every section, so one projection can be followed through minutes, usage, shooting and the rest.</p>
</div></section>

<section id="minutes"><div class="n">2</div><div><h2>Minutes and possessions</h2>
<p><span class="formula">possessions per game = minutes × pace ÷ 48</span></p>
<p>Pace hardly changes, so possessions come down to minutes. Minutes are where projections go most wrong, so this is where the model has to be right.</p>

<h3>Start: last season's minutes</h3>
<p class="claim">For established starters, last season's minutes are already close. The misses are players whose situation changed.</p>
{key_groups}
<div class="pair">{sc_last}<div>
<p>Each dot is a player who played 20+ games in '26. On the dashed line, '26 minutes matched '25 exactly; the shaded band is within 3 minutes.</p>
<ul><li>Of the {st_n} players who actually played 33+ minutes, {st_last} were within 3 of last season.</li>
<li>Same team and full seasons: {grp_counts['stable'][0]} of {grp_counts['stable'][1]} within 3. Changed teams: {grp_counts['moved'][0]} of {grp_counts['moved'][1]}. Short seasons: {grp_counts['short'][0]} of {grp_counts['short'][1]}.</li>
<li>The far-off dots are role changes: Rollins (15 → 32), Porter Jr., Tyson going up; Sochan, Mogbo, Gradey Dick going down.</li></ul></div></div>

<h3>Rejected: pulling everyone toward the middle</h3>
<p class="claim">A pull toward league-average minutes looks better on a single error number and is wrong for the players that matter.</p>
<div class="pair">{sc_flat}<div>
<p>Keeping 70% of each player's distance from 26.9 minutes squeezes the board: projections spread {sd('flat'):.1f} minutes, real minutes spread {sd('act'):.1f}. Every star drops about 3 minutes (Edwards 36.3 → 33.5; he played 35.0) and every bench player rises. Among the {st_n} heavy-minutes players it lands {st_flat} within 3, fewer than last season's {st_last}.</p></div></div>

<h3>What actually moves minutes</h3>
<p class="claim">The drift is real but depends on role, age, and the team he earned the minutes on.</p>
<p><b>Role.</b> Next-season change in minutes by last season's minutes and usage ('21→'25):</p>
{grid}
<p class="cap">High-usage players with big minutes keep them (+0.1, −0.7). Low-usage players with big minutes lose the most. Bench players gain.</p>
<p><b>Age</b>, healthy seasons only (50+ games around it, so injuries don't pass for decline):</p>
{ages}
<p><b>Team quality.</b> Minutes earned on a losing team don't last, and mostly disappear after a move:</p>
{tank}
<p><b>Short histories.</b> A player with few games is pulled toward bench minutes, but only down. The first version pulled deep-bench players up toward 16 minutes; fixed:</p>
{table(MH, fix_rows)}
<p class="cap">Tillman's base used to be '24, his last 50+ game season, in a role that was gone. With the base now needing 30 games (section 10), it is his 33-game '25.</p>

<h3>The final model against what happened</h3>
<div class="pair">{sc_fin}<div>
<p>Projections now spread {sd('final'):.1f} minutes against {sd('act'):.1f} in reality, so stars stay up and bench players stay down.</p>
<p>Where the model moved a player 2+ minutes away from last season ({len(moved2)} players), it moved him the right way {right} times ({right / len(moved2):.0%}).</p>
<p>Heavy-minutes players: {st_fin} of {st_n} within 3, against {st_last} of {st_n} for plain last-season minutes. For stars the adjustments don't beat carrying minutes forward; the gains are in the rest of the roster.</p></div></div>
<h3>Where it works</h3>
<p>Established starters on the same team, within 1.5 minutes:</p>
{works}
<h3>Where it doesn't</h3>
<p><b>Veterans whose minutes fell faster than the model expected</b> (same team, 28+ minutes):</p>
{vets_down}
<p><b>Young players who took on more</b>:</p>
{young_up}
<p><b>Role changes nothing in the box score predicted</b> (biggest overs, then biggest unders):</p>
{role}
<h3>Stars: '25, flat pull, final, actual</h3>
{star_tbl}
<h3>Pace and possessions</h3>
<p>Pace from a player's own on-court history beat using his new team's pace (2.0 vs 2.4 possessions per 48 off). Possessions follow minutes:</p>
{pace_tbl}
<h3>2026-27: the random eight</h3>
{wrap2}
</div></section>

<section id="usage"><div class="n">3</div><div><h2>Usage</h2>
<p>Usage is a player's share of his team's possessions while he's on the floor. Five players share 100%, so when a roster changes, usage has to move. The projected share scales his shots, free throws and turnovers.</p>
<h3>Start: last season's usage</h3>
{ukey}
<div class="pair">{sc_u0}<div>
<p>Players with 60+ games for their team in '25 and '26. Players who stayed are tight to the line: {s_last} of {s_n} within 1.5 points. Players who changed teams scatter: {m_last} of {m_n}.</p>
<p>Alexander-Walker went from 15.5% in Minnesota to 23.0% in Atlanta; Durant from 28% to 26%.</p></div></div>
<h3>Re-split the roster, for players who stayed</h3>
<p class="claim">When the roster around a player changes, re-splitting the team's 100% moves him the right way.</p>
<p>Every player on the new roster starts from his own usage; the team is scaled back to 100%, nobody above 40%. For players who stayed, where the re-split moved usage by a point or more, it moved the right way {rs_right} of {rs_n} times. Players within 1.5 points went from {s_last} to {s_rs} of {s_n}. It helps, modestly.</p>
{rs_tbl}
<h3>Players who changed teams keep their own</h3>
<p class="claim">The arithmetic doesn't work for movers. Their usage drifts toward the middle instead.</p>
<p>In '26 alone there are only {m_n} movers, too few to tell: {m_last} within 1.5 points keeping their own usage, {m_rs} with the re-split. Over four seasons (70 movers) the re-split did worse than keeping their own, and movers drifted toward the middle: low-usage movers gained about 1.6 points, high-usage movers lost about 1.7.</p>
{mv_tbl}
<h3>Age and role size pull usage down</h3>
<p class="claim">Older players lose usage, and high-usage players drift toward the middle, more so when they move.</p>
<p>Usage change against the re-split (or own usage for movers), '22→'26, 422 player-seasons:</p>
{age_bars}
<p class="cap">From 31 on, players lose 1–2 points more than the roster arithmetic says. Young players who changed teams went the other way (+2.5).</p>
<p>The adjustment uses age, how far his usage is above 20%, and whether he moved. Built on '22–'25 and checked on '26, it puts {n_new} of 95 players within 1.5 points, against {n_old} before. The players it moved most:</p>
{adj_tbl}
<h3>Efficiency doesn't earn usage</h3>
<p class="claim">Last season's shooting efficiency doesn't forecast next season's usage.</p>
{ts_bars}
<p class="cap">Usage change by last season's TS% quarter. No pattern. FG% against what his shot zones predict shows the same: nothing. Both were tested and left out. Shooting itself is projected zone by zone (section 4), so when a player's shot mix moves, his overall FG% moves with it.</p>
<h3>The final rule against what happened</h3>
<div class="pair">{sc_unew}<div><p>Re-split for players who stayed, own usage for movers, then the age and role-size adjustment for everyone.</p></div></div>
<h3>Older stars, 2026-27</h3>
{old_stars}
<p class="cap">Anthony Davis at 30% on a new team at 34 was too high; the adjustment brings him to 26%.</p>
<h3>2026-27: the random eight</h3>
{wrap3}
</div></section>

{sec48_html}
{sec912_html}
{outline}
</div>
"""
open(S + "per_game_projections.html", "w").write(page)
print("ok", len(page), "stars", st_last, st_flat, st_fin, st_n, "moved", right, len(moved2), "usage", s_last, s_rs, s_n, m_last, m_rs, m_n, rs_right, rs_n)
