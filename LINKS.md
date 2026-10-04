# In-page links (fantasy)

Goal: it should be hard to tap out of a page by accident. Only the **sidebar** and **top bar** move
you to another page. Every other link on a page is tracked here, by type, with how it behaves now
and how it should behave. Proposed rule: in-page links open a **pop-up card** over the page (bottom
sheet on phones); the card has a "Full page →" link for the rare time you want to leave.

Status: **real** = exists today · **planned** = will exist when that feature is built.

## Link types

| Type | What it points at | Today | Should be |
|---|---|---|---|
| Player | player page `/players/:id` | navigates (`EntityLink`) | player card pop-up |
| NBA team | NBA team page `/players/:tricode` | navigates (`EntityLink`) | NBA team card pop-up |
| Fantasy team | team page `/team/:ownerId` | navigates (`TeamLink`) | team card pop-up (roster summary, record) |
| Game | game page (none yet) | — planned | game card pop-up (box score, fantasy points) |
| Week / schedule | `/schedule?season&week` | navigates (GameLog only) | stay in page (week arrows) |

## My Team — `/team`, `/team/:ownerId`

| Element | Type | Status | Notes |
|---|---|---|---|
| Player name in each row | Player | real — navigates | → pop-up |
| NBA team name (TM / FLX rows) | NBA team | real — navigates | → pop-up |
| Headshot / team logo in a row | Player / NBA team | not a link | could open the same pop-up |
| Team switcher (dropdown) | Fantasy team | real — navigates | intended navigation; keep |
| "Team settings" button (your team) | page | real — navigates | intended; keep |
| Scorebug opponent name / logo | Fantasy team | planned | → team card pop-up |
| Schedule-view game cell (`@BOS`, `44.0`) | Game | planned | → game card pop-up |
| Week arrows | — | in-page | not a link |

## Matchup — `/matchup`

| Element | Type | Status | Notes |
|---|---|---|---|
| Team names in the matchup header | Fantasy team | real — navigates (`TeamLink`) | → pop-up |
| Player / NBA team name in each slot (both sides) | Player / NBA team | real — navigates (`EntityLink`) | → pop-up |
| Player name in the league-wide list | Player | real — navigates | → pop-up |
| Team name in the league-wide list | Fantasy team | real — navigates | → pop-up |
| Game cells (when built) | Game | planned | → game card pop-up |

## Elsewhere (for later)

- Player page game log: week labels link to `/schedule` (navigates).
- Draft room, Home, Standings also use `EntityLink` / `TeamLink`; switching those two components to
  open pop-ups changes every page at once.

When a link is added to a page, add a row here.
