// Auto-detect Hilton Honors login. Polls every 3 seconds for up to ~4 minutes
// for the activity dashboard to be loaded (URL no longer on /login/ AND a
// balance + activity row rendered).
//
// Returns JSON string:
//   {status:"logged-in", balance:<int|null>, total:<int|null>, waited_s:<int>}  ← good to proceed
//   {status:"timeout"}                                                          ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const path = location.pathname.toLowerCase();
      const notLogin = !/login|sign[-_]?in|auth/.test(path);
      const text = (document.body && document.body.innerText) || '';
      const balMatch = text.match(/([\d,]+)\s*Total Points/);
      const resultsMatch = text.match(/Results\s+\d+-\d+\s+of\s+(\d+)/i);
      if (notLogin && balMatch && resultsMatch) {
        return JSON.stringify({
          status: 'logged-in',
          balance: parseInt(balMatch[1].replace(/,/g, ''), 10),
          total: parseInt(resultsMatch[1], 10),
          waited_s: Math.round((Date.now() - start) / 1000)
        });
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
