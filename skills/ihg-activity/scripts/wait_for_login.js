// Auto-detect IHG One Rewards login. IHG is DOM-scraped (no clean API), so the
// check is: (a) the URL isn't a sign-in page, AND (b) a points balance is
// rendered somewhere on the page ("161,045 pts" or similar). Polls every 3
// seconds for up to ~4 minutes; returns immediately once both signals match.
//
// Returns JSON string:
//   {status:"logged-in", waited_s: <int>}  ← good to proceed
//   {status:"timeout"}                     ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const BAL_RE = /\b\d{1,3}(?:,\d{3})*\s*pts\b/i;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const path = (location.pathname + location.hash).toLowerCase();
      const notLogin = !/sign[-_]?in|log[-_]?in|auth/.test(path);
      const hasBalance = BAL_RE.test(document.body && document.body.innerText || '');
      if (notLogin && hasBalance) {
        return JSON.stringify({ status: 'logged-in', waited_s: Math.round((Date.now() - start) / 1000) });
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
