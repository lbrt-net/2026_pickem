#!/bin/bash
# actual-only player page for the rookie and sixth-man winners; waits for the deploy that added ?actual=true
cd "$(dirname "$0")"; export SSL_CERT_FILE=$(python3 -c "import certifi;print(certifi.where())")
for id in 1642865 1630193; do
  for i in $(seq 1 30); do
    curl -s -m 60 "https://lbrt.net/fantasy/2026_27/players/$id/page?scenario=live&actual=true" > work3/tmp_$id.json
    python3 -c "import json;h=json.load(open('work3/tmp_$id.json'))['header'];assert 'blend' not in h" 2>/dev/null && mv work3/tmp_$id.json work3/page_$id.json && echo got $id && break
    sleep 20
  done
done
