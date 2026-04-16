const BASE = import.meta.env.VITE_API_URL || "";

export async function getMe() {
  const res = await fetch(`${BASE}/me`, { credentials: "include" });
  if (!res.ok) return null;
  return res.json();
}

export async function getMatchups() {
  const res = await fetch(`${BASE}/matchups`, { credentials: "include" });
  if (!res.ok) throw new Error("Failed to load matchups");
  return res.json();
}

export async function savePick(matchupId, pick) {
  const res = await fetch(`${BASE}/picks/${matchupId}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pick),
  });
  if (!res.ok) throw new Error("Failed to save pick");
  return res.json();
}

export async function setResult(matchupId, result) {
  const res = await fetch(`${BASE}/admin/matchups/${matchupId}/result`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(result),
  });
  if (!res.ok) throw new Error("Failed to set result");
  return res.json();
}