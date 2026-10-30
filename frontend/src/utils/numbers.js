// Number formats shared by the fantasy and stats pages: a displayed negative always uses the real minus (U+2212).
export const signed = (v, d = 1) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(d)}`;
export const minus = s => String(s).replace(/^-/, "−");
