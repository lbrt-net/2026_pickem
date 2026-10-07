// The page-wide event a player / NBA team link fires to open the pop-up card (PlayerCard.jsx).
export const CARD_EVENT = "fantasy-entity-card";
export function openEntityCard(id) {
  window.dispatchEvent(new CustomEvent(CARD_EVENT, { detail: { id } }));
}

// The page's buttons for the card's header (e.g. the draft room's + Queue / Draft). A page sets them while
// it's open (null = none); the card reads them when it renders.
let cardActions = null;
export function setCardActions(fn) { cardActions = fn; }
export function getCardActions() { return cardActions; }
