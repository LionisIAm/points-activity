// Auto-detect Hyatt login. Polls the activity API every 3 seconds for up to ~4
// minutes; returns immediately once cookies are valid. The agent should call
// this AFTER navigating to /profile/en-US/account-activity, BEFORE any data
// fetch — no need to ask the user "are you logged in?" first.
//
// Returns JSON string:
//   {status:"logged-in", waited_s: <int>}  ← good to proceed
//   {status:"timeout"}                     ← user never logged in; ask them
//
// We probe the same endpoint fetch_activity.js uses (smallest page) so that
// success means BOTH that auth is valid AND the API shape is intact.
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const r = await fetch('https://www.hyatt.com/profile/api/stay/pastactivity?pageSize=1&pageIndex=0&transactionType=&locale=en-US&startDate=&endDate=', {
        credentials: 'include',
        headers: { accept: 'application/json' }
      });
      if (r.ok) {
        const j = await r.json();
        if (j && Array.isArray(j.pastActivity)) {
          return JSON.stringify({ status: 'logged-in', waited_s: Math.round((Date.now() - start) / 1000) });
        }
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
