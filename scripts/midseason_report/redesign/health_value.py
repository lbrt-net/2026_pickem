"""Value lost to missed games (2026-11-15), for Healthiest roster / Most games missed. Run inside the report work folder.

Same players and games as pipeline/health.py (rostered players; IR only when he'd have started). For each week a player
missed games: his expected weekly MAX with all his NBA team's games, minus with only the games he played, both above
replacement at his position that week (report.json repl_wk). Expected MAX of m games = the exact average best of m
draws from his own game scores this season. Missing 1 of 4 games barely moves his MAX; missing the week costs it all.
A player under replacement loses nothing. No games this season: his projected weekly max stands in.
"""
import json, os


def emax(xs, m):
    """Average best of m games drawn (with replacement) from his game scores xs."""
    if m <= 0 or not xs: return 0.0
    xs = sorted(xs); n = len(xs)
    return sum(x * ((i / n) ** m - ((i - 1) / n) ** m) for i, x in enumerate(xs, 1))


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
            pm = lambda e: P.get(e['id'], {}).get('proj_max') or 0
            starters = [x for x in t['entries'] if x['slot'] in ('G', 'F', 'C', 'FLEX')]
            for e in t['entries']:
                if e['kind'] != 'player': continue
                if e['slot'] == 'IR':
                    ok = [x for x in starters if x['slot'] in (e['position'], 'FLEX')]
                    if not ok or pm(e) <= min(pm(x) for x in ok): continue
                try:
                    dates = {g['date'] for g in logs(e['nba_team'])['games'] if g.get('week') == w and g['status'] == 'final'}
                    mine = logs(e['id'])['games']
                except FileNotFoundError:
                    continue
                pl = {g['date'] for g in mine if g.get('week') == w and (g.get('minutes') or 0) > 0}
                n, k = len(dates), len(dates & pl)
                # one pulse a week for the card's heart monitor: his weekly MAX (best game played), games played / team games
                fp = [g.get('fantasy_points') or 0 for g in mine if g.get('week') == w and (g.get('minutes') or 0) > 0 and g['date'] in dates]
                sq = a.setdefault('seq', {}).setdefault(e['id'], {'id': e['id'], 'name': e['name'], 'seq': []})
                if n: sq['seq'].append({'max': max(fp) if fp else None, 'n': n, 'k': k})
                if k >= n: continue
                xs = [g['fantasy_points'] for g in mine if (g.get('minutes') or 0) > 0 and g.get('fantasy_points') is not None]
                R = (RW.get(e['position']) or {}).get(str(w)) or 0
                if xs:
                    full, got = emax(xs, n), emax(xs, k)
                else:  # no games this season: his projected weekly max for the full week, nothing played
                    full, got = pm(e), 0.0
                lost = max(0.0, full - R) - max(0.0, got - R)
                pp = a['players'].setdefault(e['id'], {'id': e['id'], 'name': e['name'], 'missed': 0, 'lost': 0.0, 'weeks_out': 0})
                pp['missed'] += n - k; pp['lost'] += lost; pp['weeks_out'] += (k == 0)
                a['missed'] += n - k; a['lost'] += lost
    rows = []
    for a in out.values():
        a['lost'] = round(a['lost'], 1)
        a['seq'] = list(a.get('seq', {}).values())
        a['players'] = sorted(({**p, 'lost': round(p['lost'], 1)} for p in a['players'].values()), key=lambda p: (-p['lost'], -p['missed']))
        rows.append(a)
    return rows
