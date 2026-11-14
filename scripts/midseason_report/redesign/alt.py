# alt.py S GROUP -> m_alt_GROUP.html : alternative ballot look (stickers, pill meters, rounded, chunky type)
import json, sys, urllib.parse
S, G = sys.argv[1], sys.argv[2]; K = __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'kit'); W2 = f'{S}/work3'
r = json.load(open(f'{W2}/report.json')); T = r['teams']
kit = json.load(open(f'{K}/kit.json'))
P = {p['id']: p for p in json.load(open(f'{W2}/players_scenario_live.json'))}
FN = {(p.get('name') or ''): p for p in P.values()}
def hx(c): c = c.lstrip('#'); return [int(c[i:i+2], 16) for i in (0, 2, 4)]
def mix(a, b, t): return '#' + ''.join(f'{round(x*(1-t)+y*t):02x}' for x, y in zip(hx(a), hx(b)))
def lum(c): a, b, d = hx(c); return .2126*a + .7152*b + .0722*d
for k in kit.values():
    k['panel'] = k['field'] if lum(k['field']) >= 45 else mix(k['field'], '#ffffff', .16)
    k['accent'] = next((c for c in (k['secondary'], k['tertiary'], '#ffffff') if lum(c) >= 60), '#ffffff')
AL = {'GS': 'GSW', 'NY': 'NYK', 'SA': 'SAS', 'NO': 'NOP', 'PHO': 'PHX', 'UTAH': 'UTA', 'WSH': 'WAS', 'BRK': 'BKN'}
def nba_of(pid): return AL.get(P[pid].get('nba_team') or P[pid].get('team') or '', P[pid].get('nba_team') or P[pid].get('team'))
CATS = {"Scoring": [("pts","PTS",1.0),("fg3m","3PM",.5),("clutch_pts","Clutch",2.0),("fgx","Missed FG",-.5),("ftx","Missed FT",-1.0)],
        "Playmaking": [("ast","AST",1.0),("tov","TOV",-2.0)], "Boards": [("oreb","Off reb",1.5),("dreb","Def reb",.5)],
        "Stocks": [("stl","STL",2.0),("blk","BLK",1.5)]}[G]
agg = {}
for w in __import__('json').loads(__import__('os').environ.get('MS_WEEKS', '[1, 2, 3, 4]')):
    for t in json.load(open(f'{W2}/f3/wa{w}.json')).values():
        for e in t['entries']:
            if e['kind'] == 'player' and e.get('games_done') and e.get('breakdown') and e.get('week_score') is not None:
                a = agg.setdefault(e['id'], {})
                for k, _, _ in CATS: a[k] = a.get(k, 0) + e['breakdown'].get(k, 0)
top = r['mvp'][G][:3]; win = top[0]; me = agg[win['id']]
pc = next(s for s in json.load(open(f'{W2}/page_{win["id"]}.json'))['seasons'] if s['season'] == "'27")['pct']
def own(tid, cls='own'):
    t = T.get(tid)
    if not t: return f'<span class="{cls}">Free agent</span>'
    lg = r['tlogo'].get(tid); ic = f'<img src="{lg}">' if lg else f'<i style="background:{t["color"]}"></i>'
    return f'<span class="{cls}">{ic}{t["name"]}</span>'
def k_of(pid):
    ab = P.get(pid, {}).get('nba_team') or P.get(pid, {}).get('team'); ab = AL.get(ab, ab)
    return kit.get(ab) or kit['SAS']
kw = k_of(win['id'])
ordn = lambda n: 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
meters = ''
for k, lab, pt in CATS:
    v = me.get(k, 0); n = round(abs(v / pt)); p = pc[k]; good = v >= 0
    meters += (f'<div class="mt"><span class="ml">{lab}</span>'
               f'<div class="tr"><div class="fl" style="width:{p}%"></div><div class="kn" style="left:{p}%">{p}<sup>{ordn(p)}</sup></div></div>'
               f'<span class="mv">{n} <em class="{"g" if good else "b"}">{"+" if v > 0 else "−" if v < 0 else ""}{abs(v):g}</em></span></div>')
fn, _, ln = win['name'].rpartition(' ')
runners = ''.join(
    f'<div class="ru"><span class="rk">{i}</span><span class="sk sm" style="--tc:{k_of(x["id"])["panel"]}"><img src="https://cdn.nba.com/headshots/nba/latest/1040x760/{x["id"]}.png"></span>'
    f'<span class="rn"><b>{x["name"]}</b>{own(x["team"], "own s")}</span><span class="rv">{x["tot"]:.1f}</span></div>' for i, x in ((2, top[1]), (3, top[2])))
html = f'''<title>alt {G}</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=Inter:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0e1015;--card:#171a21;--line:#262a34;--text:#f2f4f7;--tc:{kw["panel"]};--ac:{kw["accent"]}}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,system-ui,sans-serif;padding:30px 40px}}
.card{{position:relative;box-sizing:border-box;width:640px;background:var(--card);border-radius:28px;padding:26px 26px 18px;overflow:hidden}}
.card:before{{content:"";position:absolute;right:-120px;top:-140px;width:420px;height:420px;border-radius:50%;
  background:radial-gradient(circle,color-mix(in srgb,var(--tc) 70%,transparent),transparent 68%);opacity:.75}}
.hd{{position:relative;display:flex;align-items:center;gap:10px;margin-bottom:18px}}
.tag{{font:800 15px "Bricolage Grotesque";letter-spacing:.02em;background:var(--text);color:var(--bg);padding:6px 14px 7px;border-radius:999px}}
.hd .sq{{width:46px;height:12px}}
.win{{position:relative;display:grid;grid-template-columns:150px 1fr auto;gap:20px;align-items:center}}
.sk{{position:relative;display:grid;place-items:center;width:150px;height:150px;border-radius:50%;background:var(--tc);
  box-shadow:0 0 0 5px var(--card),0 0 0 8px var(--ac)}}
.sk img{{width:170px;margin-top:-18px;filter:drop-shadow(3px 0 0 #fff) drop-shadow(-3px 0 0 #fff) drop-shadow(0 3px 0 #fff) drop-shadow(0 -3px 0 #fff) drop-shadow(0 6px 8px rgba(0,0,0,.45));
  position:absolute;bottom:0;margin:0;-webkit-mask:radial-gradient(circle 75px at 50% calc(100% - 75px),#000 99%,transparent 100%) bottom/100% 100% no-repeat,linear-gradient(#000,#000) top/100% 50% no-repeat}}
.sk.sm{{width:46px;height:46px;box-shadow:0 0 0 3px var(--card),0 0 0 5px var(--tc)}}
.sk.sm img{{width:56px;filter:drop-shadow(1.5px 0 0 #fff) drop-shadow(-1.5px 0 0 #fff) drop-shadow(0 -1.5px 0 #fff);-webkit-mask:radial-gradient(circle 23px at 50% calc(100% - 23px),#000 99%,transparent 100%) bottom/100% 100% no-repeat,linear-gradient(#000,#000) top/100% 50% no-repeat}}
.fn{{font:600 16px Inter}}.ln{{font:800 40px/1 "Bricolage Grotesque";letter-spacing:-.02em}}
.own{{display:inline-flex;align-items:center;gap:7px;margin-top:10px;font:700 13px Inter;background:var(--line);padding:5px 11px 5px 5px;border-radius:999px}}
.own img,.own i{{width:22px;height:22px;border-radius:50%;object-fit:cover;display:block}}
.own.s{{margin:3px 0 0;padding:3px 9px 3px 3px;font-size:12px}}.own.s img,.own.s i{{width:18px;height:18px}}
.big{{text-align:right}}.big b{{display:block;font:800 64px/.9 "Bricolage Grotesque";letter-spacing:-.03em}}
.big span{{display:inline-block;margin-top:6px;font:700 12px Inter;background:var(--ac);color:{"#0d1117" if lum(kw["accent"]) > 150 else "#f2f4f7"};padding:4px 10px;border-radius:999px}}
.band{{position:relative;display:flex;flex-direction:column;gap:14px;margin:24px 0 14px;padding:18px 22px 18px 20px;background:var(--bg);border-radius:20px}}
.mt{{display:grid;grid-template-columns:96px 1fr 88px;gap:22px;align-items:center}}.ml{{font:700 13px Inter}}.mv{{font:600 13px Inter;text-align:right;white-space:nowrap}}
.mv em{{font-style:normal;font-weight:700;margin-left:4px}}.g{{color:#4ade80}}.b{{color:#f87171}}
.tr{{position:relative;height:12px;border-radius:999px;background:var(--line)}}
.fl{{position:absolute;left:0;top:0;bottom:0;border-radius:999px;background:linear-gradient(90deg,color-mix(in srgb,var(--tc) 40%,var(--line)),var(--tc))}}
.kn{{position:absolute;top:50%;transform:translate(-50%,-50%);min-width:40px;height:28px;padding:0 6px;border-radius:999px;background:var(--text);color:var(--bg);
  display:grid;place-items:center;font:800 15px "Bricolage Grotesque";box-shadow:0 0 0 4px var(--bg)}}
.kn sup{{font-size:9px;position:relative;top:-1px}}
.kn{{display:flex;align-items:center;justify-content:center;gap:1px}}
.ru{{position:relative;display:grid;grid-template-columns:28px 46px 1fr auto;gap:12px;align-items:center;padding:10px 6px;border-top:1px dashed var(--line)}}
.rk{{display:grid;place-items:center;width:26px;height:26px;border-radius:50%;border:2px solid var(--text);font:800 13px "Bricolage Grotesque"}}
.rn b{{display:block;font:700 16px Inter}}.rv{{font:800 26px "Bricolage Grotesque"}}
</style>
<div class="card"><div class="hd"><span class="tag">{G}</span></div>
<div class="win"><span class="sk"><img src="https://cdn.nba.com/headshots/nba/latest/1040x760/{win["id"]}.png"></span>
<div><div class="fn">{fn}</div><div class="ln">{ln}</div>{own(win["team"])}</div>
<div class="big"><b>{win["tot"]:.1f}</b><span>pts from {G.lower()}</span></div></div>
<div class="band">{meters}</div>{runners}</div>'''
open(f'{S}/m_alt_{G}.html', 'w').write(html)
