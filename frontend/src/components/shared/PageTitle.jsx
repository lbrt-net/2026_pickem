import { useEffect } from "react";
import { useLocation } from "react-router-dom";

// Browser tab title for every page, from the URL: "Matchup · Fantasy 2026-27 · LBRT".
const FANTASY_SEASONS = { "2026_27": "2026-27", "2025_26": "2025-26 Test", "2027_28": "2027-28" };
const FANTASY_PAGES = [
  [/^$/, "Home"], [/^\/standings$/, "Standings"], [/^\/matchup$/, "Matchup"], [/^\/scoring$/, "Rules"],
  [/^\/replay$/, "Replay"], [/^\/league-settings$/, "League Settings"], [/^\/join$/, "Join"],
  [/^\/players$/, "Players"], [/^\/players\/[^/]+$/, "Player"], [/^\/draft$/, "Draft"], [/^\/draft\/room$/, "Draft Room"], [/^\/draft\/results$/, "Draft Results"], [/^\/draft\/recap$/, "Draft Recap"],
  [/^\/trades$/, "Trades"], [/^\/transactions$/, "Transaction Log"], [/^\/team\/settings$/, "Team Settings"],
  [/^\/team(\/[^/]+)?$/, "Roster"], [/^\/tenure$/, "History"], [/^\/playoffs$/, "Playoffs"], [/^\/recap$/, "Recap"],
];
const PICKEM_PAGES = [
  [/^$/, "Community"], [/^\/picks\/me$/, "My Picks"], [/^\/picks\/[^/]+$/, "My Picks"], [/^\/admin$/, "Admin"],
  [/^\/users$/, "Users"], [/^\/leaderboard$/, "Leaderboard"], [/^\/rules$/, "Rules"],
];

function titleFor(path) {
  const p = path.replace(/\/+$/, "");
  if (p === "") return "LBRT";
  if (p === "/account") return "Account · LBRT";
  if (p === "/admin/sitemap") return "Site Map · LBRT";
  let m = p.match(/^\/fantasy\/(\d{4}_\d{2})(.*)$/);
  if (m) {
    const page = FANTASY_PAGES.find(([re]) => re.test(m[2]))?.[1];
    return [page, `Fantasy ${FANTASY_SEASONS[m[1]] || m[1].replace("_", "-")}`, "LBRT"].filter(Boolean).join(" · ");
  }
  m = p.match(/^\/pickem\/(\d{4})(.*)$/);
  if (m) {
    const user = m[2].match(/^\/user\/([^/]+)$/);
    const page = user ? `${decodeURIComponent(user[1])}'s Picks` : PICKEM_PAGES.find(([re]) => re.test(m[2]))?.[1];
    return [page, `Pick'em ${m[1]}`, "LBRT"].filter(Boolean).join(" · ");
  }
  return "LBRT";
}

export default function PageTitle() {
  const { pathname } = useLocation();
  useEffect(() => { document.title = titleFor(pathname); }, [pathname]);
  return null;
}
