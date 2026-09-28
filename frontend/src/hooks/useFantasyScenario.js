import { useEffect, useState } from "react";

// Which fantasy sandbox to view: "live" (default), "test_pre", "test_post".
// Only admins can see test sandboxes — the server ignores this for everyone
// else and always returns live. Stored per-browser so it survives navigation.
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
