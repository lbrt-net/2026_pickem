import { useState, useSyncExternalStore } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import useCurrentUser from "../../hooks/useCurrentUser";
import UserChip from "../UserChip";
import "./MainNav.css";

const PRODUCTS = [
  { value: "pickem", label: "Pickem" },
  { value: "fantasy", label: "Fantasy" },
];

// Keep in sync with the 768px breakpoint in MainNav.css.
const DESKTOP_MQ = window.matchMedia("(min-width: 768px)");
const DESKTOP_OPEN_KEY = "mainNav.desktopSidebarOpen";

function subscribeDesktop(onChange) {
  DESKTOP_MQ.addEventListener("change", onChange);
  return () => DESKTOP_MQ.removeEventListener("change", onChange);
}

function readDesktopOpen() {
  try { return localStorage.getItem(DESKTOP_OPEN_KEY) !== "false"; } catch { return true; }
}

function Chevron() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
      <path d="M2 3.5 L5 6.5 L8 3.5" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// A dropdown whose visible face is our own span, with the real <select>
// laid invisibly over it. Browsers size a native select from its plain
// option text, so styled (uppercase, letter-spaced) text got clipped —
// the span sizes the control instead. One option = just the label.
function Picker({ className, label, value, options, onChange }) {
  const current = options.find(o => o.value === value);
  const choosable = options.length > 1;
  return (
    <div className={`main-nav-picker ${className}`}>
      <span className="main-nav-picker-face" aria-hidden={choosable || undefined}>
        {current ? current.label : value}
        {choosable && <Chevron />}
      </span>
      {choosable && (
        <select aria-label={label} value={value} onChange={e => onChange(e.target.value)}>
          {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      )}
    </div>
  );
}

// The site-wide top bar: menu button (when the page has a sidebar), LBRT
// home link, product switcher (inside pickem or fantasy), season selector
// (when applicable), user dropdown on the right. Renders its own full-width
// bar so it looks identical on landing, pickem, fantasy, and account.
//
// `sidebar` is the product's nav (pickem Sidebar / FantasySidebar). It's
// hidden until the menu button opens it as a drawer, on every screen size.
export default function MainNav({ seasonOptions, currentSeason, onSeasonChange, sidebar }) {
  const user = useCurrentUser();
  const location = useLocation();
  const navigate = useNavigate();
  const next = location.pathname + location.search;
  const product = PRODUCTS.find(p => location.pathname.startsWith(`/${p.value}`));

  // Desktop: docked open by default, collapsible, remembered across pages
  // (each page remounts MainNav). Phone: closed overlay drawer that closes
  // on navigation — remember which page it was opened on.
  const isDesktop = useSyncExternalStore(subscribeDesktop, () => DESKTOP_MQ.matches);
  const [desktopOpen, setDesktopOpen] = useState(readDesktopOpen);
  const [openOn, setOpenOn] = useState(null);
  const drawerOpen = !!sidebar && (isDesktop ? desktopOpen : openOn === location.pathname);

  function toggleDrawer() {
    if (isDesktop) {
      setDesktopOpen(!desktopOpen);
      try { localStorage.setItem(DESKTOP_OPEN_KEY, String(!desktopOpen)); } catch { /* storage unavailable */ }
    } else {
      setOpenOn(drawerOpen ? null : location.pathname);
    }
  }

  return (
    <>
      <nav className="site-ui main-nav" aria-label="Site">
        <div className="main-nav-home-block">
          {sidebar && (
            <button type="button" className="main-nav-menu" aria-label="Menu" aria-expanded={drawerOpen}
              onClick={toggleDrawer}>
              <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
                <path d="M3 5h12M3 9h12M3 13h12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
            </button>
          )}
          <Link to="/" className="main-nav-home">LBRT</Link>
        </div>
        <span className="main-nav-stripe" aria-hidden="true" />

        {product && (
          <Picker className="main-nav-product" label="Product" value={product.value}
            options={PRODUCTS} onChange={v => navigate(`/${v}`)} />
        )}

        {seasonOptions && seasonOptions.length > 0 && (
          <Picker className="main-nav-season" label="Season" value={currentSeason}
            options={seasonOptions} onChange={onSeasonChange} />
        )}

        <div className="main-nav-user">
          <UserChip user={user} next={next} extraLinks={[{ label: "Account", to: "/account" }, ...(user?.isAdmin ? [{ label: "Site Map", to: "/admin/sitemap" }] : [])]} />
        </div>
      </nav>

      {sidebar && (
        <>
          {drawerOpen && !isDesktop && <div className="main-nav-overlay" onClick={() => setOpenOn(null)} />}
          <aside className={`site-ui main-nav-drawer${drawerOpen ? " open" : ""}`} inert={!drawerOpen}>
            {sidebar}
          </aside>
        </>
      )}
    </>
  );
}
