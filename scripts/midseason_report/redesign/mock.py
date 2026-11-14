import json, sys
S = sys.argv[1]
r = json.load(open(f'{S}/work3/report.json'))
T = r['teams']; by = r['byname']
def hs(pid): return f'https://cdn.nba.com/headshots/nba/latest/1040x760/{pid}.png'
def tlogo(tid): return r['tlogo'].get(tid)
def P(name, tid, val, lab, pid=None, rk=None): return dict(name=name, tid=tid, val=val, lab=lab, pid=pid or by.get(name), rk=rk)
W = [
 *[(g, [P(x['name'], x['team'], f"{x['tot']:.1f}", f"points from {g.lower()}", x['id'], x.get('_rk')) for x in r['mvp'][g][:3]]) for g in ("Scoring", "Playmaking", "Boards", "Stocks")],
 ("Most improved", [P(x['name'], x['team'], f"+{x['gain']:.1f}", "a week over last season", x['id'], x.get('_rk')) for x in r['mip'][:3]]),
 ("Top rookie", [P(x['name'], x['team'], f"{x['tot']:.1f}", "points", x['id'], x.get('_rk')) for x in r['rookie'][:3]]),
 ("Sixth man", [P(x['name'], x['team'], f"{x['tot']:.1f}", "points on the bench", x['id'], x.get('_rk')) for x in r['sixth'][:3]]),
 ("Biggest game", [P(x['name'], x['team'], f"{x['pts']:.1f}", "points in one game") for x in r['pops'][:3]]),
 ("Best pickup", [P(x['name'], x['team'], f"+{x['per']:.1f}", "a week over replacement") for x in r['pick2'][:3]]),
 ("Most games missed", [dict(name=T[x['id']]['name'], tid=x['id'], val=str(x['games']-x['played']), lab="games missed", pid=None,
     miss=sorted(x['miss'].items(), key=lambda y:-y[1])[:3]) for x in sorted(r['health'], key=lambda x:-(x['games']-x['played']))[:3]]),
]
def first_last(n):
    w = n.split(' ')
    k = 2 if len(w) > 2 and w[-1].rstrip('.').lower() in ('jr', 'sr', 'ii', 'iii', 'iv') else 1  # 'Acuff Jr.' stays together
    return (' '.join(w[:-k]), ' '.join(w[-k:])) if len(w) > k else ('', n)
def chip(tid):
    t = T.get(tid); 
    if not t: return '<span class="chip">Free agent</span>'
    lg = tlogo(tid)
    ic = f'<img class="ti" src="{lg}">' if lg else f'<i class="ti" style="background:{t["color"]}"></i>'
    return f'<span class="chip">{ic}{t["name"]}</span>'
def pic(e, cls):
    if e['pid']: return f'<img class="{cls}" src="{hs(e["pid"])}">'
    lg = tlogo(e['tid'])
    return f'<img class="{cls} tlg" src="{lg}">' if lg else f'<i class="{cls} tlg" style="background:{T[e["tid"]]["color"]}"></i>'

BASE = '''<link href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700;800&family=Barlow+Condensed:ital,wght@0,600;0,700;0,800;1,800&display=swap" rel="stylesheet">
<style>:root{--bg:#0f1117;--surface:#161b22;--surface-2:#1c2333;--surface-3:#232b3b;--border:#30363d;--text:#e6edf3;--accent:#ff6a1f;
--fb:"Barlow",sans-serif;--fd:"Barlow Condensed",sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:var(--fb);padding:32px 40px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:28px 28px;max-width:1240px}
.ti{width:16px;height:16px;border-radius:3px;object-fit:cover;display:inline-block;vertical-align:-3px;margin-right:6px}
.chip{font-size:13px;font-weight:600;display:inline-flex;align-items:center;white-space:nowrap}
h2{font:800 15px var(--fd);letter-spacing:.14em;text-transform:uppercase;margin:0}
'''
# ---------------- 1. BALLOT ----------------
def ballot():
    css = BASE + '''
.aw{display:flex;flex-direction:column}
.aw h2{display:flex;align-items:center;gap:10px;padding-bottom:10px;border-bottom:2px solid var(--text)}
.aw h2:before{content:"";width:10px;height:16px;background:var(--accent);clip-path:polygon(40% 0,100% 0,60% 100%,0 100%)}
.r{position:relative;display:grid;grid-template-columns:44px 84px minmax(0,1fr) auto;align-items:end;gap:0 14px;border-bottom:1px solid var(--surface-3);padding:0 4px 0 0;cursor:pointer}
.r:before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--tc)}
.rk{font:800 34px/1 var(--fd);align-self:center;text-align:center;padding-left:6px}
.ph{width:84px;height:62px;object-fit:contain;object-position:bottom;background:radial-gradient(ellipse at 50% 100%,color-mix(in srgb,var(--tc) 70%,transparent),transparent 70%)}
.ph.tlg{width:44px;height:44px;border-radius:6px;margin:0 20px 9px;object-fit:cover}
.nm{padding-bottom:10px;min-width:0}.fn{font-size:13px;font-weight:600;line-height:1}.ln{font:800 24px/1.05 var(--fd);text-transform:uppercase;letter-spacing:.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nm .chip{margin-top:4px}
.v{text-align:right;padding-bottom:10px}.v b{font-size:20px;font-weight:700;display:block;font-variant-numeric:tabular-nums}.v span{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.r.win{grid-template-columns:44px 150px minmax(0,1fr) auto}.r.win:before{width:6px}
.r.win .rk{font-size:64px}.r.win .ph{width:150px;height:112px}.r.win .ph.tlg{width:80px;height:80px;margin:0 35px 14px}
.r.win .ln{font-size:40px}.r.win .v b{font:800 48px/1 var(--fd)}
.r.win{background:linear-gradient(90deg,color-mix(in srgb,var(--tc) 22%,transparent),transparent 65%)}
'''
    out = []
    for title, es in W:
        rows = []
        for i, e in enumerate(es):
            f, l = first_last(e['name'])
            team = '' if not e['pid'] else chip(e['tid'])
            rows.append(f'<div class="r{" win" if i==0 else ""}" style="--tc:{T.get(e["tid"],{}).get("color","#30363d")}"><span class="rk">{e.get("rk") or i+1}</span>{pic(e,"ph")}'
                        f'<div class="nm">{f"<div class=fn>{f}</div>" if f else ""}<div class="ln">{l}</div>{team}</div>'
                        f'<div class="v"><b>{e["val"]}</b>{"<span>"+e["lab"]+"</span>" if i==0 else ""}</div></div>')
        out.append(f'<section class="aw"><h2>{title}</h2>{"".join(rows)}</section>')
    return f'{css}</style><div class="grid">{"".join(out)}</div>'
# ---------------- 2. LOWER THIRD ----------------
def lower():
    css = BASE + '''
.aw{background:var(--surface);overflow:hidden}
.top{position:relative;height:190px;background:linear-gradient(180deg,var(--surface-2),var(--surface));overflow:hidden}
.top h2{position:absolute;left:0;top:0;background:var(--text);color:var(--bg);padding:7px 26px 7px 16px;clip-path:polygon(0 0,100% 0,calc(100% - 12px) 100%,0 100%);font-size:13px}
.top .big{position:absolute;left:18px;bottom:46px;height:150px;width:205px;object-fit:contain;object-position:bottom;z-index:1}
.top .big.tlg{width:110px;height:110px;left:46px;bottom:62px;border-radius:8px;object-fit:cover}
.bar{position:absolute;left:0;right:0;bottom:0;height:56px;display:flex;align-items:stretch;z-index:2}
.bar .nb{flex:1;background:var(--tc);display:flex;flex-direction:column;justify-content:center;padding:0 0 0 18px;clip-path:polygon(0 0,100% 0,calc(100% - 18px) 100%,0 100%);margin-right:-18px;min-width:0}
.bar .nb b{font:800 28px/1 var(--fd);text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 1px 0 rgba(0,0,0,.35)}
.bar .nb .chip{font-size:12px;margin-top:2px}
.bar .sb{background:#000;min-width:150px;display:flex;flex-direction:column;justify-content:center;align-items:flex-end;padding:0 16px 0 30px;clip-path:polygon(18px 0,100% 0,100% 100%,0 100%)}
.bar .sb b{font:800 34px/1 var(--fd)}.bar .sb span{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}
.ru{display:grid;grid-template-columns:28px 30px minmax(0,1fr) auto;gap:10px;align-items:center;height:44px;padding:0 16px 0 0;border-top:1px solid var(--surface-3);position:relative}
.ru .rk{height:100%;display:flex;align-items:center;justify-content:center;background:var(--tc);font-weight:800;font-size:15px;clip-path:polygon(0 0,100% 0,calc(100% - 6px) 100%,0 100%)}
.ru img{width:30px;height:24px;object-fit:contain;object-position:bottom}.ru img.tlg,.ru i.tlg{width:24px;height:24px;border-radius:4px;object-fit:cover}
.ru .n{font-weight:700;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ru .n .chip{margin-left:8px;font-size:12px;font-weight:500}
.ru .v{font-weight:700;font-size:16px;font-variant-numeric:tabular-nums}
'''
    out = []
    for title, es in W:
        e = es[0]; c = T.get(e['tid'],{}).get('color','#30363d')
        team = chip(e['tid']) if e['pid'] else ''
        top = (f'<div class="top" style="--tc:{c}"><h2>{title}</h2>{pic(e,"big")}<div class="bar"><div class="nb"><b>{e["name"]}</b>{team}</div>'
               f'<div class="sb"><b>{e["val"]}</b><span>{e["lab"]}</span></div></div></div>')
        rus = ''.join(f'<div class="ru" style="--tc:{T.get(x["tid"],{}).get("color","#30363d")}"><span class="rk">{x.get("rk") or i+2}</span>{pic(x,"s")}'
                      f'<span class="n">{x["name"]}{chip(x["tid"]) if x["pid"] else ""}</span><span class="v">{x["val"]}</span></div>' for i, x in enumerate(es[1:]))
        out.append(f'<section class="aw">{top}{rus}</section>')
    return f'{css}</style><div class="grid">{"".join(out)}</div>'
# ---------------- 3. POSTER ----------------
def poster():
    css = BASE + '''
.aw{position:relative;background:var(--surface);overflow:hidden}
.pos{position:relative;height:250px;overflow:hidden;background:radial-gradient(120% 90% at 85% 100%,color-mix(in srgb,var(--tc) 75%,var(--surface)),var(--surface) 70%)}
.pos h2{position:absolute;left:20px;top:16px;z-index:3}
.num{position:absolute;left:16px;top:34px;font:800 130px/1 var(--fd);letter-spacing:-.01em;z-index:1;white-space:nowrap}
.pos .big{position:absolute;right:0;bottom:0;height:210px;width:290px;object-fit:contain;object-position:right bottom;z-index:2}
.pos .big.tlg{width:130px;height:130px;right:34px;bottom:40px;border-radius:10px;object-fit:cover}
.who{position:absolute;left:20px;bottom:16px;z-index:3;max-width:58%}
.who .lab{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}
.who .v{font:800 52px/1 var(--fd)}
.who .n{font:800 22px/1.1 var(--fd);text-transform:uppercase;margin-top:6px}.who .chip{margin-top:2px}
.ru{display:grid;grid-template-columns:22px minmax(0,1fr) auto;gap:10px;align-items:center;height:40px;padding:0 20px;border-top:1px solid var(--surface-3);position:relative}
.ru:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--tc)}
.ru .rk{font-weight:800}.ru .n{font-weight:700;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ru .n .chip{margin-left:8px;font-size:12px;font-weight:500}
.ru .v{font-weight:700;font-size:16px;font-variant-numeric:tabular-nums}
'''
    out = []
    for title, es in W:
        e = es[0]; c = T.get(e['tid'],{}).get('color','#30363d')
        team = chip(e['tid']) if e['pid'] else ''
        top = (f'<div class="pos" style="--tc:{c}"><h2>{title}</h2><div class="num">{e["val"]}</div>{pic(e,"big")}'
               f'<div class="who"><div class="lab">{e["lab"]}</div><div class="n">{e["name"]}</div>{team}</div></div>')
        rus = ''.join(f'<div class="ru" style="--tc:{T.get(x["tid"],{}).get("color","#30363d")}"><span class="rk">{x.get("rk") or i+2}</span>'
                      f'<span class="n">{x["name"]}{chip(x["tid"]) if x["pid"] else ""}</span><span class="v">{x["val"]}</span></div>' for i, x in enumerate(es[1:]))
        out.append(f'<section class="aw">{top}{rus}</section>')
    return f'{css}</style><div class="grid">{"".join(out)}</div>'
for n, f in (("ballot", ballot), ("lower", lower), ("poster", poster)):
    open(f'{S}/m_{n}.html', 'w').write('<!doctype html><meta charset=utf-8>' + f())
