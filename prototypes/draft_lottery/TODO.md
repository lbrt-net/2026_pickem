# Draft order lottery — prototype (NOT wired into the site yet)

Saved 2026-10-17. `draft-lottery.html` is the standalone prototype (open it in a browser; it's also the artifact
https://claude.ai/artifact/K183dGgeRt1eiKjejsfGfE). A chrome lottery wheel spins 12 team balls; the ball nearest the
bottom gate drops out at seeded random gaps, from pick 12 up, so the last ball out picks first.

## How it works now
- **One seed drives everything.** `mulberry32(seed)` is the only random source; physics runs at a fixed 120 steps/s
  (`STEP`), so the same seed replays the identical draw on any screen. Replay was checked: run → replay → same 12-team
  order, every time (4/4 test runs).
- `newState(seed)`: balls dropped in at seeded random spots, settled 360 steps into a pile, then 420 steps (3.5 s) of
  full-speed spin before the first draw. Gaps between draws = 30–110 steps from the seed; pick 1 held longer.
- The drawn ball = nearest the gate (lightly favouring fast-moving balls). Exit: straight drop, then the rail.

## TODO — physics (commissioner, 2026-10-17: "not chaos enough")
- [x] **More chaos (2026-10-17):** balls carry spin and trade it with motion on every contact, seeded air jets from the
      floor, nearly elastic bounces, looser wall grip. Spokes are decoration on the front glass (no hits — solid spokes would trap balls in thirds). Replay still matches the original draw.
- [ ] Even more chaos if wanted. Hyper-realism not needed — it can go nuts. Right now balls cling to the wall and ride up as a
      clump; collisions don't transfer spin. Ideas: give balls angular velocity that kicks neighbours on contact (spin →
      tangential impulse), stronger spoke hits, random air-jet impulses from the seed, higher restitution, less wall drag
      so balls fly across the drum instead of sliding.
- [ ] Balls that sit just above the gate with no momentum must not be favoured (Mits / Darius kept landing 12th in early
      versions because of the starting layout). Re-check after the chaos changes.
- [ ] Keep it deterministic: every new random thing has to come from the seeded rng, and the step stays fixed.

## TODO — fairness backtest (do this BEFORE wiring it in)
- [x] **Headless check in the page** ("Fairness test" button): 600 draws in ~3 s, starting spot × pick table. First run:
      chi-square 148 on 121 df, worst cell 38% off; mild, no clear spot bias. Teams get random spots from the seed, so
      each team's odds are equal regardless; this only checks the physics.
- [ ] **Headless simulator** as a module: run `tick()` in a tight loop with no rendering and no real-time waiting (a full draw is a
      few thousand steps → milliseconds). Pull the physics + draw logic out of the page into a plain module both the
      page and the test can import.
- [ ] Backtest: for N teams (4–16), thousands of seeds → count how often each starting slot / team lands at each pick.
      Target: roughly uniform (each team ≈ 1/N at every pick; chi-square or max deviation within a few %). If a slot is
      biased, fix the physics, don't post-correct the numbers.
- [ ] Also check timing: total draw length per seed stays in a sane range (≈8–12 s at real speed).

## TODO — implementation on the site
- [ ] **Randomize order = roll the drum once on the server**: pick a seed, run the simulator headless to get the order,
      save `{seed, order}` with the draft (`fantasy_drafts.order_shuffled_at` already exists; add `lottery_seed`).
- [ ] Every open draft lobby gets the seed and plays the same animation (replaces today's `ShuffledOrder` shuffle in
      `DraftRoom.jsx`). Late joiners skip ahead to the right moment (`order_shuffled_at` + elapsed); after it ends they
      just see the order.
- [ ] Server and browser must run the *same* physics code (or the server only stores the seed and the browser's result
      is checked against the stored order) — floating-point must match; keep the math simple (no trig in the hot loop
      differences between engines) and test server-vs-browser on many seeds.
- [ ] "Replay" button in the lobby (and on the draft results page) to watch the draw again from the saved seed.
- [x] Look (2026-10-17): flat wheel, balls = the owner's Discord picture in a ring of the team color (prototype embeds
      them as small images). No Discord picture stored → team picture from the site, else Discord's default avatar.
- [ ] On the site: pull pictures from users.avatar_url / team logo_url at runtime instead of embedding.
- [ ] Phone layout (the board stacks under the wheel), reduced-motion fallback (just show the order).
