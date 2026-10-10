// Mounts the version check (version.js) for every page: every minute and whenever the tab comes back into view.
import { useEffect } from "react";
import { checkVersion } from "./version";

export default function AutoRefresh() {
  useEffect(() => {
    const t = setInterval(checkVersion, 60000);
    const onShow = () => { if (document.visibilityState === "visible") checkVersion(); };
    document.addEventListener("visibilitychange", onShow);
    return () => { clearInterval(t); document.removeEventListener("visibilitychange", onShow); };
  }, []);
  return null;
}
