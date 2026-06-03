// Auto-detect United MileagePlus login. The activity API needs an auth header
// that gets captured by the existing fetch hook, but a simpler login detector
// is the rendered balance + URL. Polls every 3 seconds for up to ~4 minutes.
//
// Returns JSON string:
//   {status:"logged-in", waited_s: <int>}  ← good to proceed
//   {status:"timeout"}                     ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const BAL_RE = /\b\d{1,3}(?:,\d{3})*\s*(miles|mi|points)\b/i;
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
