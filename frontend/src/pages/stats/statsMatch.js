// match a row's names (one player or a group) against the search box, accent-insensitive
const fold = s => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
export function matches(names, query) {
  const q = fold(query).trim();
  if (!q) return true;
  return (Array.isArray(names) ? names : [names]).some(n => fold(n).includes(q));
}
