"""Value lost to missed games (2026-11-15), for Healthiest roster / Most games missed. Run inside the report work folder.

Every rostered player, IR included. Hindsight, on actuals:
a player's normal week = his average actual weekly MAX this season over his healthy weeks (played every game; if none,
any week he played). A week he missed entirely loses all of it; a week he missed part of loses what that week's actual
MAX share it costs on average (best of k games instead of n, from his own games).
"""
import json, os


def emax(xs, m):
    """Average best of m games drawn (with replacement) from his game scores xs."""
    if m <= 0 or not xs: return 0.0
    xs = sorted(xs); n = len(xs)
    return sum(x * ((i / n) ** m - ((i - 1) / n) ** m) for i, x in enumerate(xs, 1))


# Known out on draft night (2026-10-17), per that day's reporting: through which date his absence was expected
# ('debut' = until his first game). Only that stretch is excluded; later absences count.
KNOWN_OUT = {
    '1642851': 'debut',       # Kon Knueppel: offseason hamstring strain, no timeline (debuted Nov 4; the re-injury counts)
    '202710': 'debut',        # Jimmy Butler III: ACL, target Jan-Feb 2027
    '204001': '2026-11-30',   # Kristaps Porzingis: illness, out indefinitely, "could linger into November"
    '1643407': '2026-10-21',  # AJ Dybantsa: mild ankle sprain Oct 16, day-to-day — the opener was in doubt
}


def compute(work, rep, weeks):
    J = lambda f: json.load(open(os.path.join(work, f)))
    P = {p['id']: p for p in J('players_scenario_live.json')}
    wk = {w: J(f'week_all_scenario_live_week_{w}.json') for w in weeks}
    logs = lambda i: J(f'logs2/{i}.json')
    RW = rep.get('repl_wk') or {}
    out = {}
    for w, d in wk.items():
        for tid, t in d.items():
            a = out.setdefault(tid, {'id': tid, 'lost': 0.0, 'missed': 0, 'players': {}})
            for e in t['entries']:
                if e['kind'] != 'player': continue
                # IR players always count (2026-11-15); only the stretch a player was known out on draft night is left out
                try:
                    dates = {g['date'] for g in logs(e['nba_team'])['games'] if g.get('week') == w and g['status'] == 'final'}
                    mine = logs(e['id'])['games']
                except FileNotFoundError:
                    continue
                # known out before the draft (2026-10-17 evening): the games he was expected to miss then don't count —
                # nothing missed or lost there, he was drafted / kept knowing it
                cut = KNOWN_OUT.get(e['id'], '')
                if cut == 'debut': cut = min((g['date'] for g in mine if (g.get('minutes') or 0) > 0), default='9999')
                dates = {d for d in dates if d > cut}
                if not dates: continue
                pl = {g['date'] for g in mine if g.get('week') == w and (g.get('minutes') or 0) > 0}
                n, k = len(dates), len(dates & pl)
                # one pulse a week for the card's heart monitor: his weekly MAX (best game played), games played / team games
                fp = [g.get('fantasy_points') or 0 for g in mine if g.get('week') == w and (g.get('minutes') or 0) > 0 and g['date'] in dates]
                sq = a.setdefault('seq', {}).setdefault(e['id'], {'id': e['id'], 'name': e['name'], 'seq': [], '_g': []})
                sq['_g'] += fp
                if n: sq['seq'].append({'w': w, 'max': max(fp) if fp else None, 'n': n, 'k': k})
                if k >= n: continue
                # filled in after the loop, once his healthy weeks are known (hindsight: actual weekly MAX, healthy average)
                lost = 0.0
                a.setdefault('_miss', []).append((e['id'], max(fp) if fp else None, n, k))
                pp = a['players'].setdefault(e['id'], {'id': e['id'], 'name': e['name'], 'missed': 0, 'lost': 0.0, 'weeks_out': 0})
                pp['missed'] += n - k; pp['lost'] += lost; pp['weeks_out'] += (k == 0)
                a['missed'] += n - k; a['lost'] += lost
    # value lost (hindsight on actuals): his normal week = his average actual weekly MAX over his healthy weeks (every game
    # played; none: any week he played). A fully missed week loses all of it. A partly missed week loses the share of it
    # that missing those games costs on average — best of k games instead of n, drawn from his own season's games
    # (2026-11-15: was "normal week minus that week's MAX", which charged ordinary week-to-week swings as injury: Curry
    # missed 3 games and lost 124.5 because his one healthy week was a 77).
    for a in out.values():
        healthy, games = {}, {}
        for q in a.get('seq', {}).values():
            full = [x['max'] for x in q['seq'] if x['k'] == x['n'] and x['max'] is not None]
            some = [x['max'] for x in q['seq'] if x['max'] is not None]
            healthy[q['id']] = max(0.0, sum(full) / len(full) if full else (sum(some) / len(some) if some else 0.0))
            games[q['id']] = q.pop('_g')
        a['lost'] = 0.0
        for pid, mx, n, k in a.pop('_miss', []):
            h, xs = healthy.get(pid, 0.0), games.get(pid, [])
            if mx is None or not xs: l = h
            else: l = h * (1 - emax(xs, k) / emax(xs, n)) if emax(xs, n) > 0 else 0.0
            a['players'][pid]['lost'] += l; a['lost'] += l
    rows = []
    for a in out.values():
        a['lost'] = round(a['lost'], 1)
        a['seq'] = list(a.get('seq', {}).values())
        a['players'] = sorted(({**p, 'lost': round(p['lost'], 1)} for p in a['players'].values()), key=lambda p: (-p['lost'], -p['missed']))
        rows.append(a)
    return rows
