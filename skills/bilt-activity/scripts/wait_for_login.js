// Auto-detect Bilt Rewards login. Bilt uses a JWT bearer token stored in
// localStorage (any value starting with "ey"). Polls every 3 seconds for up to
// ~4 minutes. We test the actual activity API as the most reliable signal —
// presence-of-token alone can be stale.
//
// Returns JSON string:
//   {status:"logged-in", waited_s: <int>}  ← good to proceed
//   {status:"timeout"}                     ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const start = Date.now();
  const findToken = () => {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      const v = localStorage.getItem(k) || '';
      // raw JWT
      if (v.startsWith('eyJ') && v.split('.').length === 3) return v;
      // sometimes wrapped in JSON like {"token":"ey..."}
      const m = v.match(/"(?:access_token|token|idToken)"\s*:\s*"(eyJ[^"]+)"/);
      if (m) return m[1];
    }
    return null;
  };
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const t = findToken();
      if (t) {
        const now = new Date();
        const url = `https://api.biltrewards.com/loyalty/activity?month=${now.getMonth() + 1}&year=${now.getFullYear()}`;
        const r = await fetch(url, { headers: { authorization: `Bearer ${t}`, accept: 'application/json' } });
        if (r.ok) {
          return JSON.stringify({ status: 'logged-in', waited_s: Math.round((Date.now() - start) / 1000) });
        }
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
