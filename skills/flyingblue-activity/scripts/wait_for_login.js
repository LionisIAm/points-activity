// Auto-detect Flying Blue login. The activity API is /kamino/me/transactions on
// www.flyingblue.com — session-cookie auth, no token capture needed. Probes that
// endpoint every 3 seconds for up to ~4 minutes.
//
// Returns JSON string:
//   {status:"logged-in", balance:<int>, count:<int>, waited_s:<int>}  ← good to proceed
//   {status:"timeout"}                                                ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const r = await fetch('/kamino/me/transactions', {
        credentials: 'include',
        headers: { accept: 'application/json' }
      });
      if (r.status === 200) {
        const j = await r.json();
        const balance = j && j.summary && typeof j.summary.miles === 'number' ? j.summary.miles : null;
        const count = (j && j.list && j.list.length) || 0;
        if (balance !== null) {
          return JSON.stringify({
            status: 'logged-in',
            balance,
            count,
            waited_s: Math.round((Date.now() - start) / 1000)
          });
        }
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
