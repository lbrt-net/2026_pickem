// Board geometry in inches. x = left(-)/right(+) of the board's centre line, d = distance from
// the front edge of the thrower's own board: the target runs 27-31 ft, hole centre 9 in from its top.
export const IN = 12;
export const BOARD_FRONT = 27 * IN, BOARD_BACK = 31 * IN, BOARD_HALF_W = 12;
export const HOLE = { x: 0, d: BOARD_BACK - 9 }, HOLE_R = 3;
