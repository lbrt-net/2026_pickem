// Player names in fixed-width columns (draft list, player card tables): the full name up to 16 characters;
// longer → first initial + last name ("S. Gilgeous-Alexander"); still longer → `small` (one size down).
// The draft list's Player column is the same width in every view, so the same players shorten everywhere.
export function shortName(name, cut = 16) {
  const full = name || "";
  if (full.length <= cut) return { text: full, small: false };
  const i = full.indexOf(" ");
  if (i === -1) return { text: full, small: true };
  const short = `${full[0]}. ${full.slice(i + 1)}`;
  return { text: short, small: short.length > cut };
}
