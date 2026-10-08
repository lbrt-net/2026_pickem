import { injuryKind, injuryWord } from "./injuries";
import "./injuries.css";

// The dot on a headshot's corner (the parent needs position: relative).
export function InjuryDot({ inj }) {
  const k = injuryKind(inj);
  return k ? <span className={`inj-dot ${k}`} title={`${injuryWord(inj)}${inj.injury ? ` · ${inj.injury}` : ""}`} aria-label={injuryWord(inj)} /> : null;
}
