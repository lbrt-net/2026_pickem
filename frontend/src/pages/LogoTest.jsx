import { useEffect } from "react";
import { useParams } from "react-router-dom";
import MainNav from "../components/shared/MainNav";
import useCurrentUser from "../hooks/useCurrentUser";
import LandingPage from "./LandingPage";

// Admin-only logo test (2026-11-18): the home page as it would look with each candidate logo, including the browser
// icon. The logo and icon apply on these pages only; the rest of the site keeps the plain LBRT text.
// Files in public/brand/ were cut from the commissioner's mockups (gray background keyed out).
const LOGOS = {
  1: { bar: "/brand/logo1-bar.png", full: "/brand/logo1-full.png", icon: "/brand/logo1-icon-32.png", touch: "/brand/logo1-icon-180.png" },
  2: { bar: "/brand/logo2-bar.png", full: "/brand/logo2-full.png", icon: "/brand/logo2-icon-32.png", touch: "/brand/logo2-icon-180.png" },
};

// Swap the tab icon while this page is open, put the old one back on leave.
function useTabIcon(href) {
  useEffect(() => {
    if (!href) return;
    const link = document.querySelector('link[rel="icon"]');
    if (!link) return;
    const old = { href: link.getAttribute("href"), type: link.getAttribute("type") };
    link.setAttribute("href", href); link.setAttribute("type", "image/png");
    return () => { link.setAttribute("href", old.href); if (old.type) link.setAttribute("type", old.type); };
  }, [href]);
}

export default function LogoTest() {
  const { n } = useParams();
  const user = useCurrentUser();
  const logo = user?.isAdmin ? LOGOS[n] : null;
  useTabIcon(logo?.icon);

  if (!logo) {
    return (
      <div className="site-ui" style={{ minHeight: "100vh", background: "var(--bg)" }}>
        <MainNav />
        <p style={{ padding: 24, fontSize: 14 }}>{user === undefined ? "Checking…" : user?.isAdmin ? "No such logo." : "Admins only."}</p>
      </div>
    );
  }
  return <LandingPage logo={logo} />;
}
