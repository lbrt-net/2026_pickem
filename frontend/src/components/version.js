// Open pages reload themselves when a new version of the site goes live, so nobody runs old code (mid-draft
// especially). The page knows its own build by its script file name (/assets/index-<hash>.js); it re-reads the
// site's front page every minute, when the tab comes back into view, and when the draft room's live connection
// comes back after the server restarted (= a deploy). A different script name = a new version → reload, unless
// someone's typing in a box, then on the next check.
const mine = () => document.querySelector('script[src*="/assets/index-"]')?.getAttribute("src") || null;

export async function checkVersion() {
  const current = mine();
  if (!current || import.meta.env.DEV) return;
  try {
    const html = await (await fetch("/", { cache: "no-store" })).text();
    const live = html.match(/\/assets\/index-[A-Za-z0-9_-]+\.js/)?.[0];
    const typing = document.activeElement?.matches?.("input, textarea, select") && document.activeElement.value;
    if (live && !current.endsWith(live) && !typing) window.location.reload();
  } catch {
    // offline or mid-restart: try again on the next check
  }
}
