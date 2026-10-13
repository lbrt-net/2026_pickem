import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

// Which fantasy league the pages show. The URL decides first: /fantasy/2025_26/... is the 2025-26
// test league ("replay" on the server). Under /fantasy/2026_27/... it's "live", unless an admin
// picked a sandbox ("test_pre" / "test_post") in the sidebar — that choice is stored per-browser
// (the server returns live for non-admins).
const KEY = "fantasyScenario";
const EVENT = "fantasy-scenario-change";
const SANDBOXES = ["test_pre", "test_post"];

function readSandbox() {
  try {
    const s = localStorage.getItem(KEY);
    return SANDBOXES.includes(s) ? s : "live";
  } catch {
    return "live";
  }
}

export default function useFantasyScenario() {
  const location = useLocation();
  const [sandbox, setSandbox] = useState(readSandbox);

  useEffect(() => {
    const onChange = () => setSandbox(readSandbox());
    window.addEventListener(EVENT, onChange);
    return () => window.removeEventListener(EVENT, onChange);
  }, []);

  function setScenario(value) {
    try { localStorage.setItem(KEY, value); } catch { /* storage unavailable */ }
    window.dispatchEvent(new Event(EVENT));
  }

  const scenario = location.pathname.startsWith("/fantasy/2025_26") ? "replay" : sandbox;
  return [scenario, setScenario];
}
