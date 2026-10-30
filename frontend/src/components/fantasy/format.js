import { NBA_TEAMS } from "./nbaTeams";

// Shared number / name / date formats for the fantasy pages — one format per data type (DESIGN.md "Fewer formats").

// Signed number with a real minus (U+2212): +3.4 / −2.1 / 0.0; minus() fixes a preformatted negative.
export { minus, signed } from "../../utils/numbers";

// Initial + last ("S. Gilgeous-Alexander") for grids, boards and compact rows.
export const initialLast = n => { const p = (n || "").split(" "); return p.length < 2 ? n : `${p[0][0]}. ${p.slice(1).join(" ")}`; };
// A player or NBA team in a compact row: initial + last, or the NBA team's nickname ("Thunder").
export const entityShort = e => (e?.kind === "nba_team" ? NBA_TEAMS[e.id]?.nickname || e.name : initialLast(e?.name));

// Dates and times: always the league's clock, Central (America/Chicago). Times end in " CT" (DESIGN.md).
const TZ = "America/Chicago";
// A plain league date ("2026-10-20") is a calendar day; a timestamp is shown on Central's calendar.
const asDate = v => (typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v) ? new Date(`${v}T12:00:00Z`) : new Date(v));
const fmt = (v, o) => asDate(v).toLocaleString("en-US", { timeZone: TZ, ...o });
export const ctMonthDay = v => fmt(v, { month: "short", day: "numeric" });                     // Oct 20
export const ctWeekday = v => fmt(v, { weekday: "short" });                                     // Tue
export const ctTime = v => `${fmt(v, { hour: "numeric", minute: "2-digit" })} CT`;              // 7:30 PM CT
export const ctDateTime = v => `${ctMonthDay(v)}, ${ctTime(v)}`;                                // Oct 20, 7:30 PM CT
export const ctDayDateTime = v => `${fmt(v, { weekday: "short", month: "short", day: "numeric" })}, ${ctTime(v)}`; // Tue, Oct 20, 7:30 PM CT
export const ctDayKey = v => fmt(v, { year: "numeric", month: "2-digit", day: "2-digit" });     // for same-day comparisons
// A week's dates: "Oct 20 – Oct 26".
export const dateRange = (a, b) => (a && b ? `${ctMonthDay(a)} – ${ctMonthDay(b)}` : "");
