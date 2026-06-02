// Auto-detect Aeroplan login on aircanada.com. DOM-scraped. The dashboard
// shows the points balance prominently ("75,000 points" or similar) when
// logged in. Polls every 3 seconds for up to ~4 minutes.
//
// Returns JSON string:
//   {status:"logged-in", waited_s: <int>}  ← good to proceed
//   {status:"timeout"}                     ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const BAL_RE = /\b\d{1,3}(?:,\d{3})*\s*(points|pts)\b/i;
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
