"""One rebuild at a time (2026-10-29): week_cache.single_flight and engine.kept_results.

- Viewers arriving while a rebuild for the same roster is under way wait for it instead of starting their own.
- kept_results: while one request rebuilds after a live pull (games / box scores changed only), the others get the
  copy from before that pull; a roster change is never served stale.
"""
import threading
import time

from backend.fantasy_2026_27 import engine
from backend.fantasy_2026_27.week_cache import single_flight


def test_concurrent_misses_build_once():
    inflight, lock, kept, builds = {}, threading.Lock(), {}, []

    def build():
        builds.append(1)
        time.sleep(0.2)
        kept["k"] = (0, "fp", "views")
        return "views"

    out = []
    ts = [threading.Thread(target=lambda: out.append(single_flight(inflight, lock, "k", "fp", build, lambda: kept.get("k"))))
          for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(builds) == 1 and out == ["views"] * 6 and not inflight


def test_a_newer_roster_does_not_wait_for_an_older_build():
    inflight, lock, kept, builds = {}, threading.Lock(), {}, []
    gate = threading.Event()

    def slow():
        builds.append("old")
        gate.wait(2)
        kept["k"] = (0, "old", "old views")
        return "old views"

    t = threading.Thread(target=lambda: single_flight(inflight, lock, "k", "old", slow, lambda: kept.get("k")))
    t.start()
    time.sleep(0.05)

    def fresh():
        builds.append("new")
        return "new views"

    assert single_flight(inflight, lock, "k", "new", fresh, lambda: kept.get("k")) == "new views"
    gate.set()
    t.join()
    assert builds == ["old", "new"]


def _fake(monkeypatch, fp_box, gate, built):
    monkeypatch.setattr(engine, "league", lambda cur, s: {"season": "2025-26"})
    monkeypatch.setattr(engine, "_results_fingerprint", lambda cur, s, lg: fp_box[0])

    def results(cur, s):
        built.append(fp_box[0])
        gate.wait(2)
        return {"fp": fp_box[0]}
    monkeypatch.setattr(engine, "results", results)
    engine._KEPT_RESULTS.pop("t", None)


def test_kept_results_serves_the_last_copy_during_a_live_pull_rebuild(monkeypatch):
    # fingerprint parts: rosters …, then games, box scores, league date (engine._GAME_PARTS)
    fp, gate, built = [("r1", "g1", "b1", "d")], threading.Event(), []
    _fake(monkeypatch, fp, gate, built)
    gate.set()
    first = engine.kept_results(None, "t")
    gate.clear()
    fp[0] = ("r1", "g2", "b1", "d")  # a live pull
    t = threading.Thread(target=lambda: engine.kept_results(None, "t"))
    t.start()
    time.sleep(0.05)
    assert engine.kept_results(None, "t") is first, "a second viewer gets the copy from before the pull"
    gate.set()
    t.join()
    assert engine.kept_results(None, "t") == {"fp": ("r1", "g2", "b1", "d")} and len(built) == 2


def test_kept_results_never_serves_a_roster_change_stale(monkeypatch):
    fp, gate, built = [("r1", "g1", "b1", "d")], threading.Event(), []
    _fake(monkeypatch, fp, gate, built)
    gate.set()
    engine.kept_results(None, "t")
    gate.clear()
    fp[0] = ("r1", "g2", "b1", "d")
    t = threading.Thread(target=lambda: engine.kept_results(None, "t"))
    t.start()
    time.sleep(0.05)
    fp[0] = ("r2", "g2", "b1", "d")  # a move lands while the live-pull rebuild runs
    gate.set()
    assert engine.kept_results(None, "t") == {"fp": ("r2", "g2", "b1", "d")}
    t.join()
    engine._KEPT_RESULTS.pop("t", None)
