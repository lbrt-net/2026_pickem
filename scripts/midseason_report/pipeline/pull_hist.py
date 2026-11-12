import os as _os, json as _json
BASE = _os.environ.get('MS_BASE', 'https://lbrt.net')
WEEKS = _json.loads(_os.environ['MS_WEEKS'])
import json, os, urllib.request, concurrent.futures as cf
R=json.load(open('f3/results.json'))
ids=set()
for w in R['weeks'][:len(WEEKS)]:
    for m in w['matchups']:
        for side in ('home','away'):
            for s in m[side]['slots']:
                if s['slot'] not in ('BENCH','IR'): ids.add(s['id'])
def get(i):
    p=f'f3/hist/{i}.json'
    if not os.path.exists(p):
        open(p,'w').write(urllib.request.urlopen(f'{BASE}/fantasy/2026_27/players/{i}/history?scenario=live',timeout=60).read().decode())
with cf.ThreadPoolExecutor(6) as ex: list(ex.map(get, ids))
print(len(ids))
