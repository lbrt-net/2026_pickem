#!/bin/sh
# A throwaway Postgres for the full-flow checks (tests/integration), on port 54329.
#   scripts/test_db.sh start | stop
#   TEST_DATABASE_URL=postgresql://test@localhost:54329/pickem_test pytest
DIR="${TMPDIR:-/tmp}/pickem_pgtest"
case "$1" in
  start)
    [ -d "$DIR" ] || initdb -D "$DIR" -U test --auth=trust >/dev/null
    pg_ctl -D "$DIR" -o "-p 54329 -k /tmp -c listen_addresses=localhost" -l "$DIR.log" start
    sleep 1
    psql -h localhost -p 54329 -U test -d postgres -tc "SELECT 1 FROM pg_database WHERE datname='pickem_test'" | grep -q 1 \
      || psql -h localhost -p 54329 -U test -d postgres -c "CREATE DATABASE pickem_test"
    ;;
  stop) pg_ctl -D "$DIR" stop ;;
  *) echo "usage: $0 start|stop"; exit 1 ;;
esac
