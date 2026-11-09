import { useLocation } from "react-router-dom";

// Which fantasy league the pages show, from the URL: /fantasy/2025_26/... is the 2025-26 test league ("replay" on the
// server); everything else is "live". The admin sandbox switcher (test_pre / test_post) was removed 2026-11-08.
export default function useFantasyScenario() {
  const location = useLocation();
  return [location.pathname.startsWith("/fantasy/2025_26") ? "replay" : "live"];
}
