"""Two scoring functions live here, deliberately colocated so they stay in sync:
_pick_series_pts (per-pick, used by the public leaderboard read) and
_recalculate_scores_for_matchup (full recompute, used by admin result changes)."""

ROUND_MULTIPLIERS = {1: 1, 2: 4, 3: 8, 4: 16}


def _pick_series_pts(winner, games, stat_leader, winner_result, games_result, stat_leader_result):
    pts = 0
    correct = winner and winner == winner_result
    if correct:
        pts += 2
    if games is not None and games_result is not None:
        if correct:
            dist = abs(games - games_result)
            if dist == 0: pts += 2
            elif dist == 1: pts += 1
        else:
            dist = abs(15 - games - games_result)
            if dist <= 2: pts += 1
    if stat_leader and stat_leader_result:
        leaders = [n.strip().lower() for n in stat_leader_result.split(",")]
        if stat_leader.strip().lower() in leaders:
            pts += 1
    return min(pts, 5)


def _recalculate_scores_for_matchup(cur, matchup_id: str) -> None:
    cur.execute(
        "SELECT DISTINCT user_id FROM picks WHERE matchup_id = %s",
        (matchup_id,)
    )
    affected = cur.fetchall()

    for row in affected:
        uid = row["user_id"]

        # Recalculate total points across ALL scored matchups for this user
        cur.execute("""
            SELECT
                p.winner, p.games, p.stat_leader,
                m.winner_result, m.games_result, m.stat_leader_result, m.round
            FROM picks p
            JOIN matchups m ON m.id = p.matchup_id
            WHERE p.user_id = %s
              AND m.winner_result IS NOT NULL
        """, (uid,))
        all_picks = cur.fetchall()

        total_points = 0
        for pick in all_picks:
            pts = 0
            winner_correct = pick["winner"] and pick["winner"] == pick["winner_result"]

            # Correct winner: 2 pts
            if winner_correct:
                pts += 2

            if pick["games"] is not None and pick["games_result"] is not None:
                if winner_correct:
                    dist = abs(pick["games"] - pick["games_result"])
                    if dist == 0: pts += 2
                    elif dist == 1: pts += 1
                else:
                    dist = abs(15 - pick["games"] - pick["games_result"])
                    if dist <= 2: pts += 1

            # Correct stat leader: 1 pt
            if pick["stat_leader"] and pick["stat_leader_result"]:
                result_names = [n.strip().lower() for n in pick["stat_leader_result"].split(",")]
                if pick["stat_leader"].strip().lower() in result_names:
                    pts += 1
            # Cap at 5, apply round multiplier
            mult = ROUND_MULTIPLIERS.get(pick["round"] or 1, 1)
            total_points += min(pts, 5) * mult

        cur.execute("""
            INSERT INTO scores (user_id, points)
            VALUES (%s, %s)
            ON CONFLICT(user_id) DO UPDATE SET points = EXCLUDED.points
        """, (uid, total_points))
