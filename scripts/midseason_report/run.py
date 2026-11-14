"""Build the Mid-Season Report end to end (2026-11-12): pull from the site, run the pipeline, render one HTML page.

    python3 scripts/midseason_report/run.py [--base https://lbrt.net] [--out midseason.html]

Weeks = every regular-season week that has started (the current one with its games so far), capped at week 9 —
the report's cut-off. Prints one JSON line last: {"weeks": [...], "final": true once week 9 is final, "html": path}.
The site runs this nightly (backend/fantasy_2026_27/midseason.py) and freezes the copy built after week 9 is final.
Every step has a time cap and logs to <work>/log.txt, so a stuck pull fails instead of hanging.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LAST_WEEK = 9
STEPS = ["patch", "health", "bench", "balance", "tg", "pull_hist", "luck", "extra", "pick", "draftkept", "v2data", "icons2"]
RENDER = ["aw.js", "aw.css", "body.html", "build_v1.py", "splice.py", "swap_aw.py"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://lbrt.net")
    ap.add_argument("--out", default="midseason.html")
    ap.add_argument("--work", default=None)
    a = ap.parse_args()
    base = a.base.rstrip("/")
    work = a.work or tempfile.mkdtemp(prefix="midseason-")
    for d in ("f3/hist", "icons", "logs2"):
        os.makedirs(os.path.join(work, d), exist_ok=True)
    log = open(os.path.join(work, "log.txt"), "a", buffering=1)

    def say(*x):
        print(*x, file=log, flush=True)

    def get(path, timeout=120):
        url = f"{base}/fantasy/2026_27/{path}{'&' if '?' in path else '?'}scenario=live"
        for i in range(3):
            try:
                return urllib.request.urlopen(url, timeout=timeout).read().decode()
            except Exception as e:  # noqa: BLE001
                say("retry", path, e)
                time.sleep(5)
        raise RuntimeError(f"pull failed: {path}")

    def put(name, text):
        with open(os.path.join(work, name), "w") as f:
            f.write(text)

    results = get("results")
    R = json.loads(results)
    today = R["as_of"][:10]
    weeks = [w["week"] for w in R["weeks"] if w["kind"] == "regular" and w["start"] <= today and w["week"] <= LAST_WEEK]
    final = any(w["week"] == LAST_WEEK and w["status"] == "final" for w in R["weeks"])
    cur = min(R["current_week"], LAST_WEEK)
    say("weeks", weeks, "final", final, "cur", cur)
    put("results_scenario_live.json", results); put("f3/results.json", results)
    simple = {"teams": ["teams_scenario_live.json", "f3/teams.json"], "players": ["players_scenario_live.json"],
              "players/actual?window=season": ["players_actual_scenario_live_window_season.json"],
              "draft": ["draft_scenario_live.json"], "transactions": ["transactions_scenario_live.json", "f3/tx.json"]}
    jobs = [(p, names) for p, names in simple.items()]
    for w in weeks:
        jobs.append((f"week/all?week={w}", [f"week_all_scenario_live_week_{w}.json", f"f3/wa{w}.json"]))
        jobs.append((f"players/week-scores?week={w}", [f"ws{w}.json", f"f3/ws{w}.json"]))
    jobs.append((f"week/all?week={cur}", ["f3/wa_cur.json"]))
    with ThreadPoolExecutor(4) as ex:
        for (p, names), text in zip(jobs, ex.map(lambda j: get(j[0]), jobs)):
            for n in names:
                put(n, text)
    say("pulled", len(jobs))

    teams = json.load(open(os.path.join(work, "teams_scenario_live.json")))
    rep = {"teams": {t["id"]: {"name": t["name"], "color": t["color"], "owner": t.get("owner_name"), "ab": t.get("abbreviation"),
                               "glyph": t.get("glyph")} for t in teams}}
    put("report.json", json.dumps(rep))

    env = dict(os.environ, MS_BASE=base, MS_WEEKS=json.dumps(weeks), MS_CUR=str(cur),
               MS_GLYPHS=os.path.join(REPO, "frontend/src/components/fantasy/glyphs.js"))
    for s in STEPS:
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, "pipeline", s + ".py")], cwd=work, env=env,
                           capture_output=True, text=True, timeout=900)
        say(f"step {s} {time.time() - t0:.0f}s rc={r.returncode}\n{r.stdout[-2000:]}{r.stderr[-4000:]}")
        if r.returncode:
            raise RuntimeError(f"step {s} failed: {r.stderr[-800:]}")
    # redesigned cards (redesign/build_cards.py): added to report.json as D.cards; a failure keeps the old look
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(HERE, "redesign", "build_cards.py")], cwd=work, env=env,
                       capture_output=True, text=True, timeout=900)
    say(f"step cards {time.time() - t0:.0f}s rc={r.returncode}\n{r.stdout[-2000:]}{r.stderr[-4000:]}")
    for f in RENDER:
        shutil.copy(os.path.join(HERE, f), os.path.join(work, f))
    for cmd in (["swap_aw.py"], None, ["splice.py"], ["build.py"]):
        if cmd is None:
            shutil.copy(os.path.join(work, "build_v1.py"), os.path.join(work, "build.py"))
            continue
        r = subprocess.run([sys.executable, cmd[0]], cwd=work, capture_output=True, text=True, timeout=300)
        if r.returncode:
            raise RuntimeError(f"render {cmd[0]} failed: {r.stderr[-800:]}")
    body = open(os.path.join(work, "midseason.html")).read()
    html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>'
            + body + "</body></html>")
    with open(a.out, "w") as f:
        f.write(html)
    print(json.dumps({"weeks": weeks, "final": final, "html": os.path.abspath(a.out), "work": work}))


if __name__ == "__main__":
    main()
