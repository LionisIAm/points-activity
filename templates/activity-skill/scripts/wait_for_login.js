// TEMPLATE — auto-detect login for <Program>. Poll every 3s for up to ~4 minutes.
// Pick ONE detection strategy and delete the other.
//
// Returns JSON string:
//   {status:"logged-in", balance:<int|null>, waited_s:<int>}  ← good to proceed
//   {status:"timeout"}                                         ← ask the user to log in
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      // --- Strategy A: API programs — probe an auth-gated endpoint ---------
      // const r = await fetch('/api/<activity-endpoint>', {credentials:'include',
      //   headers:{accept:'application/json'}});
      // if (r.status === 200) {
      //   const j = await r.json();
      //   return JSON.stringify({status:'logged-in', balance: j.<balanceField> ?? null,
      //     waited_s: Math.round((Date.now()-start)/1000)});
      // }

      // --- Strategy B: DOM programs — URL not on /sign-in AND a balance renders ---
      const path = (location.pathname + location.hash).toLowerCase();
      const notLogin = !/sign[-_]?in|log[-_]?in|auth/.test(path);
      const text = (document.body && document.body.innerText) || '';
      const balMatch = text.match(/([\d,]+)\s*(?:points|miles|avios)/i);  // TODO: tune
      if (notLogin && balMatch) {
        return JSON.stringify({
          status: 'logged-in',
          balance: parseInt(balMatch[1].replace(/,/g, ''), 10),
          waited_s: Math.round((Date.now() - start) / 1000)
        });
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
