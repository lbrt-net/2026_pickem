// Fantasy navigation, shared by FantasySidebar (sections + links) and
// FantasyShell (title + tabs). A link with `tabs` is a main page whose
// sub-pages show as tabs on the page; the sidebar keeps one entry for it,
// highlighted on any of its tabs.
export const SECTIONS = [
  {
    label: "League",
    links: [
      { label: "Home", path: "" },
      { label: "Standings", path: "/standings" },
      { label: "Matchup", path: "/matchup" },
      { label: "Schedule", path: "/schedule" },
      { label: "Playoffs", path: "/playoffs" },
      { label: "Recap", path: "/recap" },
      { label: "Draft", path: "/draft", tabs: [
        { label: "Draft Room", path: "/draft" },
        { label: "Draft Recap", path: "/draft/recap" },
      ] },
    ],
  },
  {
    label: "Roster",
    links: [
      { label: "My Team", path: "/team", tabs: [
        { label: "Lineup", path: "/team" },
        { label: "History", path: "/tenure" },
        { label: "Settings", path: "/team/settings" },
      ] },
      { label: "Players", path: "/players" },
      { label: "Trades", path: "/trades" },
      { label: "Transactions", path: "/transactions" },
    ],
  },
];

// Is `link` the current page? Tab groups match any of their tabs exactly;
// other links also match their detail pages (e.g. /players/:id).
export function isLinkActive(link, base, pathname) {
  if (link.tabs) return link.tabs.some(t => pathname === base + t.path);
  if (link.path === "") return pathname === base;
  return pathname === base + link.path || pathname.startsWith(`${base}${link.path}/`);
}

// The tab group (main page) the current path belongs to, if any.
export function findTabGroup(base, pathname) {
  for (const section of SECTIONS) {
    for (const link of section.links) {
      if (link.tabs && isLinkActive(link, base, pathname)) return link;
    }
  }
  return null;
}
