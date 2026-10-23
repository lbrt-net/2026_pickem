import { useEffect, useState } from "react";

// One shared store of server data for the visit (2026-10-21). A page asking for something already loaded gets it at
// once; if it's older than FRESH it's shown anyway and refreshed quietly behind (the page updates when it lands).
// Anything sent to the server (a move, add/drop, trade, claim) marks everything old, so your own change shows on the
// next look. Nothing is stored past closing the tab.
const FRESH = 30000;
const C = new Map();     // url -> { data, at, p }
const SUBS = new Map();  // url -> Set of re-render callbacks

function emit(url) {
  for (const f of SUBS.get(url) || []) f();
}

let bundle = null;  // the first page's bundle, while it's on its way (warmup.js startBundle)

function fetchNow(url) {
  const p = fetch(url, { credentials: "include" })
    .then(r => (r.ok ? r.json() : null)).catch(() => null)
    .then(data => { C.set(url, { data, at: Date.now(), p: null }); emit(url); return data; });
  C.set(url, { ...(C.get(url) || {}), p });
  return p;
}

export function load(url, force = false) {
  const e = C.get(url);
  if (e?.p) return e.p;
  if (!force && e && "data" in e && Date.now() - e.at < FRESH) return Promise.resolve(e.data);
  if (!force && bundle && !(e && "data" in e)) {
    // the page bundle is coming: wait for it, and fetch on our own only if it didn't carry this
    const p = bundle.then(() => {
      const n = C.get(url);
      if (n && "data" in n && n.at) return n.data;
      if (n) n.p = null;
      return fetchNow(url);
    });
    C.set(url, { ...(e || {}), p });
    return p;
  }
  return fetchNow(url);
}

// a page bundle's piece, filed under the address the page would have fetched
export function seed(url, data) {
  C.set(url, { data, at: Date.now(), p: null });
  emit(url);
}

export function bundleFirst(promise) {
  bundle = promise.catch(() => {}).finally(() => { bundle = null; });
}

const peek = url => { const e = C.get(url); return e && "data" in e ? e.data : undefined; };

// undefined while loading the first time, null if it failed, else the data (possibly a moment old while refreshing)
export function useCached(url) {
  const [, bump] = useState(0);
  useEffect(() => {
    if (!url) return undefined;
    const f = () => bump(n => n + 1);
    if (!SUBS.has(url)) SUBS.set(url, new Set());
    SUBS.get(url).add(f);
    load(url);
    return () => SUBS.get(url)?.delete(f);
  }, [url]);
  return url ? peek(url) : undefined;
}

export const prefetch = url => { load(url); };

// a change sent to the server: everything is old now; what's on screen refreshes right away
function staleAll() {
  for (const [url, e] of C) {
    e.at = 0;
    if (SUBS.get(url)?.size) load(url, true);
  }
}

if (typeof window !== "undefined" && !window.__fantasyCache) {
  window.__fantasyCache = true;
  const orig = window.fetch.bind(window);
  window.fetch = (input, init) => {
    const p = orig(input, init);
    if ((init?.method || "GET").toUpperCase() !== "GET") p.then(() => staleAll()).catch(() => {});
    return p;
  };
}
