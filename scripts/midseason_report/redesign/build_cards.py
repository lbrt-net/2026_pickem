"""Build the redesigned cards (2026-11-14) inside a report work folder and add them to report.json as D.cards.

Run by run.py after the pipeline steps, with cwd = the work folder and the same env (MS_BASE, MS_WEEKS).
Each card is a standalone HTML page; aw.js mounts it in a sealed frame (no style clashes with the old page) and
scales it to the column. A card that fails to build is left out, and that award keeps the old look.
Cards: the 4 MVP groups, Most improved, Top rookie, Sixth man, All-Fantasy, and the superlatives Biggest game,
Best game on the bench, Steadiest player, Most up-and-down. Every other superlative stays as it is.
"""
import json, os, subprocess, sys, urllib.request

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
ids = {r["mvp"][g][0]["id"] for g in r["mvp"] if r["mvp"][g]} | {r[k][0]["id"] for k in ("mip", "rookie", "sixth") if r.get(k)}
for i in ids:
    try:
        open(f"page_{i}.json", "w").write(get(f"players/{i}/page?actual=true"))
    except Exception as e:  # noqa: BLE001
        say("page", i, e)
# the projection saved before the bench-game week (commissioner page; skipped without the key)
if r.get("bench"):
    wk = r["bench"][0]["week"]
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
       'min-width:{W}px!important;box-sizing:border-box}.lbl{display:none!important}</style>')
cards = {}


def take(name, fname):
    html = open(os.path.join(S, fname)).read()
    fit = FIT.replace("{W}", "1100" if name == "All-Fantasy" else "664")
    cards[name] = html.replace("</style>", "</style>" + fit, 1) if "</style>" in html else fit + html


try:
    run("mock.py")
except Exception as e:  # noqa: BLE001
    say("mock", e)
for g in ("Scoring", "Playmaking", "Boards", "Stocks", "Most improved", "Top rookie", "Sixth man"):
    try:
        run("sc_g.py", g)
        for step in ("flair2.py", "flair3g.py", "flair4.py", "flair9g.py"):
            run(step)
        take(g, "m_card.html")
    except Exception as e:  # noqa: BLE001
        say("card", g, e)
for name, args, fname in (("All-Fantasy", ("af.py",), "m_af.html"),
                          ("Biggest game", ("sup_big.py",), "m_sup_biggest.html"),
                          ("Best game on the bench", ("sup.py",), "m_sup_bench.html"),
                          ("Steadiest player", ("sup_cons.py", "steady"), "m_sup_steady.html"),
                          ("Most up-and-down", ("sup_cons.py", "swing"), "m_sup_swing.html")):
    try:
        run(*args)
        take(name, fname)
    except Exception as e:  # noqa: BLE001
        say("card", name, e)
r["cards"] = cards
json.dump(r, open("report.json", "w"))
say("built", sorted(cards), sum(len(v) for v in cards.values()) // 1024, "KB")
print(json.dumps({"cards": sorted(cards)}))
