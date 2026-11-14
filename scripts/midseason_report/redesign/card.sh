#!/bin/bash
# card.sh GROUP -> m_card_GROUP.png  (mock of one award card in the approved look)
set -e
G=$1; S=$PWD; R=$(cd "$(dirname "$0")" && pwd)
export SSL_CERT_FILE=$(python3 -c "import certifi;print(certifi.where())")
python3 $R/mock.py $S >/dev/null
for id in $(python3 -c "import json;r=json.load(open('work3/report.json'));print(' '.join(e['id'] for g in [*r['mvp'].values(), r['mip'], r['rookie'], r['sixth']] for e in g[:3]))"); do
  [ -s hs/$id.png ] || curl -s -m 20 -o hs/$id.png https://cdn.nba.com/headshots/nba/latest/1040x760/$id.png
done
python3 $R/mock.py $S >/dev/null
python3 $R/sc_g.py $S "$G" >/dev/null
python3 $R/flair2.py $S && python3 $R/flair3g.py $S && python3 $R/flair4.py $S && python3 $R/flair9g.py $S
cp m_card.html "m_card_$G.html"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars --force-device-scale-factor=2 --window-size=760,520 --virtual-time-budget=1500 --screenshot="$S/m_card_$G.png" "file://$S/m_card_$G.html" 2>/dev/null
echo "$S/m_card_$G.png"
