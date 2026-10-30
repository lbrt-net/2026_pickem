import { useEffect, useRef } from "react";

// A table's header row that stays under the site bar while the page scrolls past a long table (2026-10-29). The
// table's own sideways scroller keeps CSS sticky from reaching the page, so a copy of the header floats above it:
// shown only while the real header is under the bar, its cell widths copied from the real one, and kept in step when
// the table scrolls sideways. scrollRef goes on the table's scroller, floatRef on the copy's wrapper
// (<div class="lc-float"><div><table><thead>…</thead></table></div></div>).
export default function useFloatHead(deps) {
  const scrollRef = useRef(null), floatRef = useRef(null);
  useEffect(() => {
    const sc = scrollRef.current, fl = floatRef.current;
    if (!sc || !fl) return undefined;
    const inner = fl.firstElementChild;
    const sync = () => {
      const real = sc.querySelector("thead"), table = sc.querySelector("table"), copy = inner?.querySelector("table");
      if (!real || !table || !copy) return;
      const nav = document.querySelector(".main-nav");
      const y = nav ? Math.max(0, nav.getBoundingClientRect().bottom) : 0;
      const head = real.getBoundingClientRect(), body = table.getBoundingClientRect();
      const on = head.top < y && body.bottom > y + head.height;
      fl.classList.toggle("on", on);
      if (!on) return;
      fl.style.top = `${y}px`;
      copy.style.width = `${body.width}px`;
      const a = real.querySelectorAll("th"), b = copy.querySelectorAll("th");
      a.forEach((th, i) => { if (b[i]) b[i].style.width = `${th.getBoundingClientRect().width}px`; });
      inner.scrollLeft = sc.scrollLeft;
    };
    sync();
    window.addEventListener("scroll", sync, { passive: true });
    window.addEventListener("resize", sync);
    sc.addEventListener("scroll", sync, { passive: true });
    return () => {
      window.removeEventListener("scroll", sync);
      window.removeEventListener("resize", sync);
      sc.removeEventListener("scroll", sync);
    };
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return { scrollRef, floatRef };
}
