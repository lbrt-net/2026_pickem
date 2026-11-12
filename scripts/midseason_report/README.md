# Mid-Season Report (and End of Season Report)

**Live on the site, admin only: https://lbrt.net/reports/midseason** (2026-11-12) — rebuilt nightly after the box
scores (and on boot if missing) by `run.py`, covering every week that has started through week 9; the copy built once
week 9 is final is frozen (backend/fantasy_2026_27/midseason.py; force a rebuild: POST /reports/midseason/build).
Run it by hand: `python3 scripts/midseason_report/run.py --out ms.html` (`pipeline/` = the compute scripts with weeks
from env, not hard-coded).

First published as a private claude.ai artifact:
https://claude.ai/artifact/LE44j9Ng1Zd2uV3hacvD6p (draft built 2026-11-08/09 on weeks 1–3, commissioner liked it).

- **Mid-Season Report** = the season to date, cut off after **week 9**. Final edits by weeks 7–8.
- **End of Season Report** = the full regular season, before the playoffs.
- The page never says "Weeks 1–N". Titles are "Mid-Season Report" / "End of Season Report"; award names have no
  "of the year" (they work in both reports).
- Later: build it into the site (plan at the bottom).

## Layout (top to bottom)
1. **Awards** — the "standard" awards, half-width cards:
   - **MVP × 4, one per wheel group** (the player page wheel: Scoring = pts, 3PM, clutch, FG-, FT-, BLKD;
     Playmaking = AST, TO; Boards = OREB, DREB; Stocks = STL, BLK). Points that group earned him in his weekly best
     games, added up over the season.
   - **Most improved** — this season's average weekly best minus last season's (last season needs 10+ weeks).
   - **Top rookie** — no prior NBA season in our history; total of weekly bests.
   - **Sixth man** — most points scored while on a fantasy bench (weekly bests in BENCH weeks, summed per team).
2. **All-Fantasy Teams** (1st/2nd/3rd) — one per spot (G, F, C, Flex = next best player, TEAM). Ranked by the
   weekly bests added up; a missed week counts as zero. Headshot / NBA logo on the owner's color, owner's icon + name.
3. **Superlatives** — the rest, all half width, in pairs:
   - Best game on the bench (bench player's best minus the starter he could have replaced, `_fits`) | Biggest game
     (both show the box line + every fantasy part as tiles: gains first, green edge; losses after, red edge; the
     site's labels, e.g. FG-, are kept as is)
   - Best pickup (points over the week's replacement level at his position, averaged over weeks he started for the
     team that added him) | Steadiest player
   - Most up-and-down | Same lineup
   - Revolving door (faces of every starter used) | Most balanced
   - One-man team (balance = each week, the top starter's share of that week's starter points, averaged — so
     rotating starters doesn't count against you) | Healthiest roster
   - Most games missed (IR counts only if he'd have started: yes Duren, no Butler; who missed shown with counts;
     0 missed shows nobody) | Unluckiest
   - Just for fun (players a team added who never started for it) | Stuck with the draft (drafted dollars still on
     the roster, faces + prices)
   Steadiest / up-and-down = standard deviation of weekly bests, only weeks on the team he's listed under, 3+ weeks.

**Unluckiest** (settled after many rounds — don't redo it): count only **losses** where the opponent's starters ran
hotter than yours, measured against each starter's own usual week (median weekly best, last 2 seasons + this one).
Starting bad players is not bad luck: a bad player playing to his low usual adds nothing. Rank by how many such
losses, then the average swing. The card shows two numbers per loss: **his guys** (points below their usual) and
**their guys** (points above theirs). No percentiles shown, no week list. No Luckiest award.

## Every award card
Winner open on top: picture (headshot, or the fantasy team's icon — uploaded picture, else its glyph on its color,
never a blank square), name, the team's icon + name under a player, then the numbers big with a short caps label
under each. 2nd and 3rd are one-line rows (rank, small picture, name, team icon + name, number); **click a row to
open it and collapse the others**. One short line at most — no sentences, no explainers.

## How the draft was built (scratch pipeline, run from a working folder)
1. Pull from the live site (scenario=live): `teams`, `results`, `players`, `players/actual?window=season`, `draft`,
   `transactions`, `week/all?week=N`, `players/week-scores?week=N`, `/players/{id}/history`,
   `/entity/{TEAM}/games` (`compute/tg.py`).
2. `compute/patch.py` (All-Fantasy, cont, cons, draft value), `health.py`, `bench.py`, `balance.py`, then
   `luck.py`, `extra.py` (unlucky, balance, consistency, just for fun), `pick.py` (weekly replacement levels + best
   pickup), `draftkept.py`, `v2data.py` (MVP groups, sixth man, MIP, rookie), `icons2.py` (headshots, NBA logos,
   team pictures embedded as data URIs — artifacts can't load outside images). `WEEKS = [1, 2, 3]` is hard-coded.
3. Render: `python3 swap_aw.py && cp build_v1.py build.py && python3 splice.py && python3 build.py` →
   `midseason.html` (aw.js / aw.css hold the awards, MVP and All-Fantasy).

## Into the site (later)
- Backend: a `midseason` builder next to `recap.py` (same inputs it already has: `_games`, lineups, history,
  `draft_value` replacement levels), saved in `fantasy_recaps` as kind `midseason` / `final`, frozen once built,
  rebuilt only by restat — same as weekly recaps.
- Frontend: a tab on Recap; reuse PlayerCard / TeamIcon / headshot helpers instead of embedded images; award cards
  as one component (open winner + clickable rows).
- Add to DECISIONS.md (each award's rule above) and CLEARED.md when it lands.
