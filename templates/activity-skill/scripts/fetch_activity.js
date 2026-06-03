// TEMPLATE (API path) — run in a logged-in <domain> tab via javascript_tool.
// Calls the program's internal JSON API, normalizes rows, stashes them on
// window.__exact, and returns a small summary. Keep this file OR scrape_activity.js
// (delete the one you don't use).
//
// ENDPOINT: TODO document method, URL, params, pagination (0-based vs 1-based!),
// page-size limits, auth header, response shape. Preserve quirks in comments.
(async () => {
  // TODO: replace with the real request. If a bare fetch 401/403s, the SPA attaches
  // an auth header at runtime — capture it via an XHR hook (see other sub-skills'
  // capture_auth.js) and replay here.
  const r = await fetch('/api/<activity-endpoint>', {
    method: 'GET',
    credentials: 'include',
    headers: { accept: 'application/json' }
  });
  if (r.status !== 200) {
    return JSON.stringify({ error: 'HTTP ' + r.status + ' — not logged in / stale token?' });
  }
  const j = await r.json();

  // Normalize to flat rows. Field order for dump_console.js: date ~~ kind ~~ desc ~~ amount
  const iso = (d) => (d || '').slice(0, 10);
  const rows = ((j && j.activities) || []).map((a) => ({
    date: iso(a.date),
    kind: a.amount < 0 ? 'R' : 'E',          // TODO: your real classifier signal
    description: (a.description || '').trim(),
    amount: a.amount || 0
  }));

  window.__exact = rows;
  const sum = rows.reduce((s, x) => s + (x.amount || 0), 0);
  const dates = rows.map((x) => x.date).filter(Boolean).sort();
  return JSON.stringify({
    count: rows.length,
    totalSum: sum,
    oldest: dates[0] || null,
    newest: dates[dates.length - 1] || null
  });
})();
