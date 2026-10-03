import { useEffect, useState } from "react";

// Which fantasy league to view: "live" (default), "replay" (the 2025-26 test league — anyone,
// picked from the season dropdown), or the admin-only "test_pre" / "test_post" sandboxes (the
// server returns live for non-admins). Stored per-browser so it survives navigation.
const KEY = "fantasyScenario";
const EVENT = "fantasy-scenario-change";

function read() {
  try { return localStorage.getItem(KEY) || "live"; } catch { return "live"; }
}

export default function useFantasyScenario() {
  const [scenario, setScenarioState] = useState(read);

  useEffect(() => {
    const onChange = () => setScenarioState(read());
    window.addEventListener(EVENT, onChange);
    return () => window.removeEventListener(EVENT, onChange);
  }, []);

  function setScenario(value) {
    try { localStorage.setItem(KEY, value); } catch { /* storage unavailable */ }
    window.dispatchEvent(new Event(EVENT));
  }

  return [scenario, setScenario];
}
