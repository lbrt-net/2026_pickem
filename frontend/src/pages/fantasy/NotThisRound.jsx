import { Link } from "react-router-dom";
import FantasyShell from "../../components/fantasy/FantasyShell";
import { base, SEASON } from "../../components/fantasy/data";

// Shown for fantasy pages switched off in features.js.
export default function NotThisRound() {
  return (
    <FantasyShell title="Not in this round" season={SEASON}>
      <p style={{ fontSize: 14 }}>
        This page is switched off while we test the core league (draft, players, roster, scoring, schedule, playoffs).
        It comes back in a later round. <Link to={base()}>Back to fantasy home</Link>
      </p>
    </FantasyShell>
  );
}
