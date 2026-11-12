import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json, base64, io, os, urllib.request, concurrent.futures as cf
from PIL import Image
J=lambda f: json.load(open(f))
IDS=dict(ATL=1610612737,BOS=1610612738,CLE=1610612739,NOP=1610612740,CHI=1610612741,DAL=1610612742,DEN=1610612743,GSW=1610612744,HOU=1610612745,LAC=1610612746,LAL=1610612747,MIA=1610612748,MIL=1610612749,MIN=1610612750,BKN=1610612751,NYK=1610612752,ORL=1610612753,IND=1610612754,PHI=1610612755,PHX=1610612756,POR=1610612757,SAC=1610612758,SAS=1610612759,OKC=1610612760,TOR=1610612761,UTA=1610612762,MEM=1610612763,WAS=1610612764,DET=1610612765,CHA=1610612766)
NAMES=dict(ATL='Atlanta Hawks',BOS='Boston Celtics',BKN='Brooklyn Nets',CHA='Charlotte Hornets',CHI='Chicago Bulls',CLE='Cleveland Cavaliers',DAL='Dallas Mavericks',DEN='Denver Nuggets',DET='Detroit Pistons',GSW='Golden State Warriors',HOU='Houston Rockets',IND='Indiana Pacers',LAC='LA Clippers',LAL='Los Angeles Lakers',MEM='Memphis Grizzlies',MIA='Miami Heat',MIL='Milwaukee Bucks',MIN='Minnesota Timberwolves',NOP='New Orleans Pelicans',NYK='New York Knicks',OKC='Oklahoma City Thunder',ORL='Orlando Magic',PHI='Philadelphia 76ers',PHX='Phoenix Suns',POR='Portland Trail Blazers',SAC='Sacramento Kings',SAS='San Antonio Spurs',TOR='Toronto Raptors',UTA='Utah Jazz',WAS='Washington Wizards')
byname={p['name']:p['id'] for p in J('players_scenario_live.json')}
byname.update({v:k for k,v in NAMES.items()})
rep=J('report.json')
names=set()
names|={x['name'] for x in rep['pops']}|{x['bench'] for x in rep['bench']}|{x['start'] for x in rep['bench']}
names|={x['name'] for v in rep['cons'].values() for x in v}|{x['name'] for x in rep['pick2']}
names|={w['name'] for x in rep['balance'] for w in x['weeks']}|{n for x in rep['health'] for n in x['miss']}
names|={p['name'] for x in rep['forfun'] for p in x['players']}|{p['name'] for x in rep['cont'] for p in x['used']}
ids={byname[n] for n in names if n in byname}|{x[0] for d in rep['draft'] for x in d['still']}|set(rep.get('extra_ids',[]))
print('unmapped',[n for n in names if n not in byname])
def fetch(url,p):
    if not os.path.exists(p):
        open(p,'wb').write(urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read())
def get(i):
    url=f'https://cdn.nba.com/logos/nba/{IDS[i]}/primary/D/logo.svg' if i in IDS else f'https://cdn.nba.com/headshots/nba/latest/260x190/{i}.png'
    try: fetch(url,f'icons/{i}')
    except Exception as e: print('fail',i,e)
teams=J('teams_scenario_live.json')
def getteam(t):
    u=t.get('logo_url')
    if not u: return
    if u.startswith('/'): u=BASE+u
    try: fetch(u,f"icons/team_{t['id'].split(':')[1]}")
    except Exception as e: print('fail team',t['name'],e)
with cf.ThreadPoolExecutor(8) as ex: list(ex.map(get,ids)); list(ex.map(getteam,teams))
icons=rep.get('icons',{})
def enc(path,size):
    b=open(path,'rb').read()
    if b[:5]==b'<?xml' or b[:4]==b'<svg': return 'data:image/svg+xml;base64,'+base64.b64encode(b).decode()
    im=Image.open(io.BytesIO(b)).convert('RGBA'); im.thumbnail(size); o=io.BytesIO(); im.save(o,'WEBP',quality=82)
    return 'data:image/webp;base64,'+base64.b64encode(o.getvalue()).decode()
for i in ids:
    if os.path.exists(f'icons/{i}'): icons[i]=enc(f'icons/{i}',(176,128))
tl={}
for t in teams:
    p=f"icons/team_{t['id'].split(':')[1]}"
    if os.path.exists(p): tl[t['id']]=enc(p,(96,96))
rep['icons']=icons; rep['tlogo']=tl; rep['byname']={n:byname[n] for n in names if n in byname}
json.dump(rep,open('report.json','w'))
print(len(icons),len(tl),sum(len(v) for v in icons.values())//1024+sum(len(v) for v in tl.values())//1024,'KB')
