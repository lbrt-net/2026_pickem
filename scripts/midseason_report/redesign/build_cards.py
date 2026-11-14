"""Build the redesigned cards (2026-11-14) inside a report work folder and add them to report.json as D.cards.

Run by run.py after the pipeline steps, with cwd = the work folder and the same env (MS_BASE, MS_WEEKS).
Each card is a standalone HTML page; aw.js mounts it in a sealed frame (no style clashes with the old page) and
scales it to the column. A card that fails to build is left out, and that award keeps the old look.
Cards: the 4 MVP groups, Most improved, Top rookie, Sixth man, All-Fantasy, and the superlatives Biggest game,
Best game on the bench, Steadiest player, Most up-and-down. Every other superlative stays as it is.
"""
import json, os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.getcwd()
BASE = os.environ.get("MS_BASE", "https://lbrt.net").rstrip("/")
S = os.path.join(WORK, "_rd")
os.makedirs(S, exist_ok=True)
if not os.path.exists(os.path.join(S, "work3")):
    os.symlink(WORK, os.path.join(S, "work3"))
log = open(os.path.join(WORK, "log.txt"), "a", buffering=1)
say = lambda *x: print("[cards]", *x, file=log, flush=True)


def get(path, key=False):
    req = urllib.request.Request(f"{BASE}/fantasy/2026_27/{path}{'&' if '?' in path else '?'}scenario=live")
    if key and os.environ.get("INTERNAL_API_KEY"):
        req.add_header("X-Internal-Key", os.environ["INTERNAL_API_KEY"])
    return urllib.request.urlopen(req, timeout=120).read().decode()


r = json.load(open("report.json"))
# the player page's season rows (actual numbers only) for every card winner: percentiles come from there
ids = {x["id"] for g in r["mvp"] for x in r["mvp"][g][:3]} | {x["id"] for k in ("mip", "rookie", "sixth") for x in r.get(k, [])[:3]}
for i in ids:
    try:
        open(f"page_{i}.json", "w").write(get(f"players/{i}/page?actual=true"))
    except Exception as e:  # noqa: BLE001
        say("page", i, e)
# the projection saved before the bench-game week (commissioner page; skipped without the key)
for wk in {x["week"] for x in r.get("bench", [])[:3]}:
    try:
        open(f"projcheck_w{wk}.json", "w").write(get(f"projection-check?week={wk}", key=True))
    except Exception as e:  # noqa: BLE001
        say("projection check", e)
        open(f"projcheck_w{wk}.json", "w").write('{"rows": []}')


def run(*args):
    p = subprocess.run([sys.executable, os.path.join(HERE, args[0]), S, *args[1:]], capture_output=True, text=True, timeout=300)
    if p.returncode:
        raise RuntimeError(p.stderr[-600:])


# laid out at its designed width (the frame scales it down to the column), on the report's page color
FIT = ('<style>html,body{margin:0!important;background:#0f1117!important}body{padding:0 12px 12px 0!important;'
       'min-width:{W}px!important;box-sizing:border-box}.lbl{display:none!important}'
       '.pv[hidden]{display:none!important}.pv{animation:pvin .2s ease-out}@keyframes pvin{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}.r:not(.win),.ru{cursor:pointer}</style>')
# a click on 2nd / 3rd (or back on 1st) shows that place's version; the frame resizes itself
SWITCH = """<script>
// keep 1-2-3 order: in the version where place k is open, the rows ranked above k sit above it
document.querySelectorAll(".pv").forEach(v => {
  const k = +v.dataset.r, hero = v.querySelector(".r.win, .win"); if (!hero || k < 2) return;
  const rows = [...v.querySelectorAll(".r:not(.win), .ru")].filter(x => +(x.querySelector(".rk") || {}).textContent < k);
  rows.forEach(x => hero.parentNode.insertBefore(x, hero));
});
document.addEventListener("click", e => {
  const row = e.target.closest(".r:not(.win), .ru"); if (!row) return;
  const k = (row.querySelector(".rk") || {}).textContent; if (!k) return;
  document.querySelectorAll(".pv").forEach(v => v.hidden = v.dataset.r !== k.trim());
});</script>"""
ORIG = json.load(open("report.json"))
LISTS = {g: ("mvp", g) for g in ("Scoring", "Playmaking", "Boards", "Stocks")}
LISTS.update({"Most improved": ("mip",), "Top rookie": ("rookie",), "Sixth man": ("sixth",), "Biggest game": ("pops",),
              "Best game on the bench": ("bench",), "Steadiest player": ("cons", "steady"), "Most up-and-down": ("cons", "swing")})


def with_place(name, k):
    """report.json with place k first in this award's list (each entry keeps its real rank as _rk)."""
    rep = json.loads(json.dumps(ORIG)); node = rep
    for key in LISTS[name][:-1]: node = node[key]
    top = [dict(x, _rk=i + 1) for i, x in enumerate(node[LISTS[name][-1]][:3])]
    if k > len(top): return False
    node[LISTS[name][-1]] = [top[k - 1]] + [x for x in top if x is not top[k - 1]]
    json.dump(rep, open("report.json", "w"))
    return True


def split(html):
    """(head: links + styles, body) of a built card page."""
    cut = html.rindex("</style>") + len("</style>")
    return html[:cut], html[cut:]


cards = {}


def build(name, steps, fname):
    heads, bodies = [], []
    for k in (1, 2, 3):
        if not with_place(name, k): break
        for st in steps: run(*st)
        h, b = split(open(os.path.join(S, fname)).read())
        heads.append(h); bodies.append(f'<div class="pv" data-r="{k}"{"" if k == 1 else " hidden"}>{b}</div>')
    json.dump(ORIG, open("report.json", "w"))
    # one stylesheet: every version holds the same three players, so the same team rules (only their order differs);
    # rules a later version adds that the first lacks are appended
    head = heads[0]
    for h in heads[1:]:
        for rule in re.findall(r"[^{}]+\{[^{}]*\}", h):
            if rule not in head: head = head.replace("</style>", rule + "</style>", 1)
    cards[name] = head + FIT.replace("{W}", "664") + "".join(bodies) + SWITCH


try:
    run("mock.py")
except Exception as e:  # noqa: BLE001
    say("mock", e)
for g in ("Scoring", "Playmaking", "Boards", "Stocks", "Most improved", "Top rookie", "Sixth man"):
    try:
        build(g, [("mock.py",), ("sc_g.py", g), ("flair2.py",), ("flair3g.py",), ("flair4.py",), ("flair9g.py",)], "m_card.html")
    except Exception as e:  # noqa: BLE001
        json.dump(ORIG, open("report.json", "w")); say("card", g, e)
for name, steps, fname in (("Biggest game", [("sup_big.py",)], "m_sup_biggest.html"),
                           ("Best game on the bench", [("sup.py",)], "m_sup_bench.html"),
                           ("Steadiest player", [("sup_cons.py", "steady")], "m_sup_steady.html"),
                           ("Most up-and-down", [("sup_cons.py", "swing")], "m_sup_swing.html")):
    try:
        build(name, steps, fname)
    except Exception as e:  # noqa: BLE001
        json.dump(ORIG, open("report.json", "w")); say("card", name, e)
try:  # All-Fantasy: one page, nothing to expand
    run("af.py")
    h = open(os.path.join(S, "m_af.html")).read()
    cards["All-Fantasy"] = h.replace("</style>", "</style>" + FIT.replace("{W}", "1100"), 1)
except Exception as e:  # noqa: BLE001
    say("card", "All-Fantasy", e)
r = ORIG
r["cards"] = cards
json.dump(r, open("report.json", "w"))
say("built", sorted(cards), sum(len(v) for v in cards.values()) // 1024, "KB")
print(json.dumps({"cards": sorted(cards)}))
