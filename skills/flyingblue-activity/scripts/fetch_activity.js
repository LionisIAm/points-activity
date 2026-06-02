// Flying Blue activity fetcher — run via javascript_tool (javascript_exec) in a
// logged-in www.flyingblue.com tab. Calls the dashboard's internal JSON API and
// flattens transactions + details into a single list on window.__fbact. Dump to
// console with the next script and read back via read_console_messages.
//
// ENDPOINT (GET):
//   https://www.flyingblue.com/kamino/me/transactions
//   - No path params; session cookie is the only auth.
//   - Response: { summary: { miles: <int balance>, ... }, list: [ ... ] }.
//     Each list entry: { date, description?, milesAmount, xpAmount,
//                        details: [ { date, description, milesAmount, xpAmount } ] }.
//     ActivityType is implicit in the sign of milesAmount (- = redemption,
//     + = earning). XP/qualifying is IGNORED (not a spendable currency).
//
// Flatten rule:
//   - miles>0 top-level → ONE earn row using top-level (date, description).
//     If description is null, fall back to first detail's description.
//   - miles<0 top-level → ONE redeem row per detail entry whose miles != 0
//     (preserves per-passenger / per-segment granularity for award bookings).
//     Uses detail.date (the travel date) rather than top-level.date (booking date).
//   - miles==0 top-level → check details: if their sum is non-zero, emit by
//     the same rules using the details' sign; if zero too, skip (XP-only or
//     future placeholder).
//
// Output row shape: { date: 'YYYY-MM-DD', kind: 'E'|'R', description, miles }
(async () => {
  const r = await fetch('/kamino/me/transactions', {
    method: 'GET',
    credentials: 'include',
    headers: { accept: 'application/json' }
  });
  if (r.status !== 200) {
    return JSON.stringify({ error: 'HTTP ' + r.status + ' — not logged in?' });
  }
  const j = await r.json();
  const balance = (j.summary && j.summary.miles) || 0;
  const list = (j && j.list) || [];

  const iso = (d) => (d || '').slice(0, 10);
  const rows = [];

  for (const t of list) {
    const tDate = iso(t.date);
    const tDesc = t.description || ((t.details && t.details[0] && t.details[0].description) || '');
    const tMiles = t.milesAmount || 0;
    const details = t.details || [];

    if (tMiles > 0) {
      rows.push({ date: tDate, kind: 'E', description: tDesc, miles: tMiles });
    } else if (tMiles < 0) {
      // Expand redemption to per-detail rows
      for (const d of details) {
        const dMiles = d.milesAmount || 0;
        if (dMiles === 0) continue;
        rows.push({
          date: iso(d.date) || tDate,
          kind: dMiles < 0 ? 'R' : 'E',
          description: d.description || tDesc,
          miles: dMiles
        });
      }
      // Fallback: if no details produced rows, keep the top-level
      if (!details.some(d => d.milesAmount)) {
        rows.push({ date: tDate, kind: 'R', description: tDesc, miles: tMiles });
      }
    } else {
      // tMiles == 0: rely on details
      const dSum = details.reduce((s, d) => s + (d.milesAmount || 0), 0);
      if (dSum === 0) continue; // XP-only or empty
      for (const d of details) {
        const dMiles = d.milesAmount || 0;
        if (dMiles === 0) continue;
        rows.push({
          date: iso(d.date) || tDate,
          kind: dMiles < 0 ? 'R' : 'E',
          description: d.description || tDesc,
          miles: dMiles
        });
      }
    }
  }

  window.__fbact = rows;
  const sum = rows.reduce((s, r) => s + (r.miles || 0), 0);
  const dates = rows.map(r => r.date).sort();
  return JSON.stringify({
    count: rows.length,
    totalMilesSum: sum,
    balance,
    oldest: dates[0] || null,
    newest: dates[dates.length - 1] || null
  });
})();
