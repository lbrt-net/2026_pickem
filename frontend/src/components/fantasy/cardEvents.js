// The page-wide event a player / NBA team link fires to open the pop-up card (PlayerCard.jsx).
export const CARD_EVENT = "fantasy-entity-card";
export function openEntityCard(id) {
  window.dispatchEvent(new CustomEvent(CARD_EVENT, { detail: { id } }));
}
