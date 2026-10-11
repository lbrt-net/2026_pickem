// What device this page is really on, for the Devices list ("iPad · Firefox"). The browser's ID string lies on iOS:
// an iPad in desktop mode says "Mac", and every iOS browser says "Safari". The page can tell: a "Mac" with a
// touchscreen is an iPhone or iPad (by screen size); Firefox and Chrome for iOS leave their own objects on the page.
export function deviceName() {
  const ua = navigator.userAgent || "";
  // iOS in desktop mode claims to be a Mac; a touchscreen gives it away, and screen size says phone or tablet
  const touchMac = /Macintosh/.test(ua) && navigator.maxTouchPoints > 1;
  const small = Math.min(window.screen.width, window.screen.height) < 600;
  const device = (/iPhone/.test(ua) || (touchMac && small)) ? "iPhone" : (/iPad/.test(ua) || touchMac) ? "iPad" : /Android/.test(ua) ? "Android"
    : /Macintosh/.test(ua) ? "Mac" : /Windows/.test(ua) ? "Windows" : /CrOS/.test(ua) ? "Chromebook" : /Linux/.test(ua) ? "Linux" : "Device";
  const ios = device === "iPhone" || device === "iPad";
  const browser = (window.__firefox__ || /FxiOS|Firefox/.test(ua)) ? "Firefox"
    : /EdgiOS|EdgA|Edg\//.test(ua) ? "Edge"
    : /OPR\/|OPT\//.test(ua) ? "Opera"
    : /SamsungBrowser/.test(ua) ? "Samsung Internet"
    : (window.__gCrWeb || /CriOS/.test(ua) || (!ios && /Chrome/.test(ua))) ? "Chrome"
    : /Safari/.test(ua) ? "Safari" : "Browser";
  return `${device} · ${browser}`;
}

// Android (and other Chromium browsers) can tell a site the exact model when asked — "Pixel 8 Pro", "SM-S928U" —
// and the real browser brand. iPhones never give a model (Apple doesn't expose one), so iOS stays "iPhone".
export async function deviceNameDetailed() {
  const base = deviceName();
  const ua = navigator.userAgentData;
  if (!ua?.getHighEntropyValues) return base;
  try {
    const v = await ua.getHighEntropyValues(["model", "platform"]);
    const brand = (ua.brands || []).map(b => b.brand).find(b => !/Not.?A.?Brand|Chromium/i.test(b)) || "";
    const browser = /Edge/i.test(brand) ? "Edge" : /Samsung/i.test(brand) ? "Samsung Internet" : /Opera/i.test(brand) ? "Opera"
      : /Chrome/i.test(brand) ? "Chrome" : base.split(" · ")[1];
    const device = v.platform === "Android" ? ((v.model || "").trim() || "Android") : base.split(" · ")[0];
    return `${device} · ${browser}`;
  } catch {
    return base;
  }
}
