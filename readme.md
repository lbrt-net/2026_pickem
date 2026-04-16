# Setting Matchup Times

## How lock_time works

You **never set lock_time directly**. You set `game_time` in Central Time and the server calculates `lock_time` automatically as **1 hour before tip-off**.

---

## Creating or updating a matchup

POST to `/admin/matchups` with JSON. Requires admin cookie (be logged in as admin).

```json
{
  "id": "r1-east-bos-phi",
  "label": "Boston vs Philadelphia",
  "team_a": "Boston",
  "team_b": "Philadelphia",
  "seed_a": 1,
  "seed_b": 8,
  "conference": "East",
  "round": 1,
  "stat_label": "Points",
  "game_time": "2026-04-19T13:00"
}
```

### `game_time` format

```
YYYY-MM-DDTHH:MM
```

Always **Central Time**. No timezone suffix — the server assumes Central.

| Game tip-off (CT) | game_time value       | Locks at (CT) |
|-------------------|-----------------------|---------------|
| Sat Apr 19 1:00pm | `2026-04-19T13:00`    | 12:00pm CT    |
| Sat Apr 19 3:30pm | `2026-04-19T15:30`    | 2:30pm CT     |
| Sat Apr 19 6:00pm | `2026-04-19T18:00`    | 5:00pm CT     |
| Sat Apr 19 8:30pm | `2026-04-19T20:30`    | 7:30pm CT     |

---

## TBD matchups

Set `team_a` and/or `team_b` to `null` (or omit them) when the opponent isn't known yet. The frontend will show the matchup but make it unclickable. Update once teams are set:

```json
{
  "id": "r1-west-okc-tbd",
  "label": "OKC vs TBD",
  "team_a": null,
  "team_b": "Oklahoma City",
  "seed_b": 1,
  "conference": "West",
  "round": 1,
  "game_time": "2026-04-19T15:30"
}
```

Once the opponent is determined, re-POST the same `id` with `team_a` filled in. Existing picks are preserved.

---

## First round 2026 — game times to paste in

Copy these directly. Edit team names once play-in results are final.

```json
{ "id": "r1-east-tor-cle", "label": "Toronto @ Cleveland",   "team_a": "Toronto",      "team_b": "Cleveland",     "seed_a": 8, "seed_b": 1, "conference": "East", "round": 1, "game_time": "2026-04-18T13:00" }
{ "id": "r1-east-atl-nyk", "label": "Atlanta @ New York",    "team_a": "Atlanta",      "team_b": "New York",      "seed_a": 7, "seed_b": 2, "conference": "East", "round": 1, "game_time": "2026-04-18T18:00" }
{ "id": "r1-east-phi-bos", "label": "Philadelphia @ Boston", "team_a": "Philadelphia", "team_b": "Boston",        "seed_a": 8, "seed_b": 1, "conference": "East", "round": 1, "game_time": "2026-04-19T13:00" }
{ "id": "r1-east-tbd-det", "label": "TBD @ Detroit",         "team_a": null,           "team_b": "Detroit",       "seed_a": null, "seed_b": 4, "conference": "East", "round": 1, "game_time": "2026-04-19T18:30" }
{ "id": "r1-west-min-den", "label": "Minnesota @ Denver",    "team_a": "Minnesota",    "team_b": "Denver",        "seed_a": 7, "seed_b": 2, "conference": "West", "round": 1, "game_time": "2026-04-18T15:30" }
{ "id": "r1-west-hou-lal", "label": "Houston @ LA Lakers",   "team_a": "Houston",      "team_b": "LA Lakers",     "seed_a": 8, "seed_b": 1, "conference": "West", "round": 1, "game_time": "2026-04-18T20:30" }
{ "id": "r1-west-tbd-okc", "label": "TBD @ Oklahoma City",   "team_a": null,           "team_b": "Oklahoma City", "seed_a": null, "seed_b": 1, "conference": "West", "round": 1, "game_time": "2026-04-19T15:30" }
{ "id": "r1-west-por-sas", "label": "Portland @ San Antonio","team_a": "Portland",     "team_b": "San Antonio",   "seed_a": 8, "seed_b": 1, "conference": "West", "round": 1, "game_time": "2026-04-19T21:00" }
```

---

## How to POST these (curl)

```bash
curl -X POST https://YOUR_DOMAIN/admin/matchups \
  -H "Content-Type: application/json" \
  -b "session=YOUR_SESSION_COOKIE" \
  -d '{ ...matchup json... }'
```

Get your session cookie from browser devtools → Application → Cookies after logging in as admin.

---

## Future rounds

Same process. Once series are set:
1. Create matchup with `team_a`/`team_b` = `null` and the scheduled `game_time`
2. Re-POST with actual teams filled in once they're determined
3. The lock recalculates automatically on every upsert