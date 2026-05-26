// Hyatt account-activity fetcher — run via javascript_tool (javascript_exec) in a
// logged-in hyatt.com tab. Returns {count, oldest, newest} and stashes raw rows
// on window.__hyattRows. Then dump rows to console with dumpHyatt() and read them
// back via read_console_messages (raw JSON return is often blocked by the chat).
//
// IMPORTANT API QUIRKS (learned the hard way):
//   - Pagination is 0-BASED. pageIndex=0 is the NEWEST page. Starting at 1 silently
//     drops the most recent ~15 transactions.
//   - Large pageSize breaks (pageSize>=200 returns []). Use pageSize=15.
//   - Stop when response.showLoadMoreButton === false (cleaner than length checks).
(async () => {
  const PAGE = 15, MAX_PAGES = 40;
  let all = [];
  for (let p = 0; p < MAX_PAGES; p++) {
    const url = `https://www.hyatt.com/profile/api/stay/pastactivity?pageSize=${PAGE}&pageIndex=${p}&transactionType=&locale=en-US&startDate=&endDate=`;
    const r = await fetch(url, { headers: { accept: 'application/json' }, credentials: 'include' });
    if (!r.ok) return JSON.stringify({ error: 'HTTP ' + r.status + ' — likely not logged in' });
    const j = await r.json();
    const a = j.pastActivity || [];
    all = all.concat(a);
    if (!j.showLoadMoreButton || a.length < PAGE) break;
  }
  // de-dupe by transaction id
  const seen = new Set(), uniq = [];
  for (const x of all) { const id = x.transaction.id; if (!seen.has(id)) { seen.add(id); uniq.push(x); } }
  window.__hyattRows = uniq;
  const dates = uniq.map(x => x.transaction.date).sort();
  return JSON.stringify({ count: uniq.length, oldest: dates[0], newest: dates[dates.length - 1] });
})();
