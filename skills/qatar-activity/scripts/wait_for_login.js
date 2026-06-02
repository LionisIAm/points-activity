// Auto-detect Qatar Airways Privilege Club login. Polls the rendered dashboard
// for the balance display + activity table for up to ~4 minutes (3s interval).
//
// Returns JSON string:
//   {status:"logged-in", balance:<int>, count:<int>, waited_s:<int>}  ← good to proceed
//   {status:"timeout"}                                                ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  // Balance number like "175,121" appears as a standalone block on the dashboard
  const BAL_RE = /\b\d{1,3}(?:,\d{3})+\s*(?:Total balance|Avios)?/i;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const path = (location.pathname + location.hash).toLowerCase();
      const notLogin = !/sign[-_]?in|log[-_]?in|auth/.test(path);
      const text = (document.body && document.body.innerText) || '';
      const hasBalance = /Total balance/i.test(text) && BAL_RE.test(text);
      // Table check
      const tbl = Array.from(document.querySelectorAll('table')).find(t =>
        t.rows.length > 1 &&
        Array.from(t.rows[0].cells).some(c => /transaction date/i.test((c.innerText || '')))
      );
      if (notLogin && hasBalance && tbl) {
        // Extract balance
        const m = text.match(/(\d{1,3}(?:,\d{3})+)\s+Total balance/i);
        const bal = m ? parseInt(m[1].replace(/,/g, ''), 10) : null;
        return JSON.stringify({
          status: 'logged-in',
          balance: bal,
          count: tbl.rows.length - 1,
          waited_s: Math.round((Date.now() - start) / 1000)
        });
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
