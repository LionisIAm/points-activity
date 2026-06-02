// Auto-detect Accor ALL login. The data path uses a Bearer JWT from
// localStorage; visible balance shows as "12 345 pts" / "12,345 pts" on the
// statement page. Polls every 3 seconds for up to ~4 minutes.
//
// Returns JSON string:
//   {status:"logged-in", waited_s: <int>}  ← good to proceed
//   {status:"timeout"}                     ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const BAL_RE = /\b\d{1,3}(?:[ ,. ]\d{3})*\s*pts\b/i;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const path = (location.pathname + location.hash).toLowerCase();
      const notLogin = !/sign[-_]?in|log[-_]?in|account\/login|connexion/.test(path);
      const txt = document.body && document.body.innerText || '';
      const hasBalance = BAL_RE.test(txt);
      if (notLogin && hasBalance) {
        return JSON.stringify({ status: 'logged-in', waited_s: Math.round((Date.now() - start) / 1000) });
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
