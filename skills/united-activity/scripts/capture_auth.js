// United auth-capture — run ONCE per session BEFORE fetch_activity.js.
// United's activity API needs an `x-authorization-api: bearer <token>` header that
// the SPA attaches at runtime (not in localStorage). This arms an XHR hook, then you
// trigger a real activity request so the hook can grab the header.
//
// USAGE:
//   1. Run this script (arms the hook).
//   2. In the SAME tab, trigger a re-fetch of activity — e.g. click "Recent activity"
//      then "Collapse all rows", or change the date filter. (Do this via javascript:
//      click a button whose text matches /recent activity|collapse all|expand all/i.)
//   3. Re-run this script with mode 'read' (or just read window.__unitedAuth) to
//      confirm the token was captured. Then run fetch_activity.js.
(() => {
  if (window.__unitedAuth && window.__unitedAuth.xAuth) {
    return JSON.stringify({ alreadyCaptured: true, preview: window.__unitedAuth.xAuth.slice(0, 12) });
  }
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.setRequestHeader, on = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; this.__h = {}; return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.setRequestHeader = function (k, v) { if (this.__h) this.__h[k.toLowerCase()] = v; return os.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (b) {
    try {
      if (this.__u && /Activities/i.test(this.__u) && this.__h && this.__h['x-authorization-api']) {
        window.__unitedAuth = { xAuth: this.__h['x-authorization-api'], lang: this.__h['accept-language'] || 'en-US' };
      }
    } catch (e) {}
    return on.apply(this, arguments);
  };
  return JSON.stringify({ armed: true, next: 'trigger an activity re-fetch (e.g. click "Recent activity"/"Collapse all rows"), then check window.__unitedAuth' });
})();
