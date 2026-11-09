import json, urllib.request, concurrent.futures as cf
AB="ATL BOS BKN CHA CHI CLE DAL DEN DET GSW HOU IND LAC LAL MEM MIA MIL MIN NOP NYK OKC ORL PHI PHX POR SAC SAS TOR UTA WAS".split()
def get(ab):
    g=json.load(urllib.request.urlopen(f'https://lbrt.net/fantasy/2026_27/entity/{ab}/games?scenario=live',timeout=60))['games']
    out={}
    for x in g:
        if x['status']=='final' and x['week'] in (1,2,3) and x['fantasy_points'] is not None:
            out[x['week']]=max(out.get(x['week'],-99),x['fantasy_points'])
    return ab,out
with cf.ThreadPoolExecutor(6) as ex: d=dict(ex.map(get,AB))
json.dump(d,open('f3/tg.json','w')); print(d['CLE'])
