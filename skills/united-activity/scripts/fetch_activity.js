// United MileagePlus activity fetcher — run via javascript_tool (javascript_exec)
// in a logged-in united.com activity tab. Calls United's internal activity API and
// stashes activities on window.__uact. Dump to console with the next script and read
// back via read_console_messages.
//
// ENDPOINT (GET):
//   https://www.united.com/api/myunited/account/Activities/StartDate=YYYY-MM-DD~EndDate=YYYY-MM-DD/<limit>
//   - StartDate/EndDate bound the window; <limit> caps rows. Use a wide range and a
//     big limit (e.g. 500) to get everything in one call.
//   - Response: { data: { activities: [ ... ] } }. Each activity has ActivityType
//     ('F' = flight, 'O' = other/earning), Description, TransactionDate, TotalMiles
//     (final mile amount, already includes all bonus components), plus PQP/PQF/PQS
//     (Premier-qualifying — IGNORED for the miles table), IsRedeposit, PartnerName.
//
// AUTH — THE CRITICAL BIT: a plain GET returns 405. The request needs the header
//   x-authorization-api: bearer <token>
// That token is NOT in localStorage — it's a runtime value the SPA attaches. The
// only reliable way to get it is to capture a real request the page makes. This
// script first checks window.__unitedAuth (set by the auth-capture step); if missing,
// it returns an error telling you to run the capture step.
//
// AUTH CAPTURE STEP (run BEFORE this script, once per session):
//   1. Arm an XHR hook that records the x-authorization-api header of any URL
//      matching /Activities/, into window.__unitedAuth.
//   2. Trigger a real activity request by clicking the "Recent activity" control (or
//      "Collapse all rows" / changing the date filter) — anything that re-fetches.
//   See scripts/capture_auth.js.
(async () => {
  const A = window.__unitedAuth;
  if (!A || !A.xAuth) {
    return JSON.stringify({ error: 'No auth token. Run scripts/capture_auth.js first to capture x-authorization-api.' });
  }
  const today = new Date().toISOString().slice(0, 10);
  const url = `https://www.united.com/api/myunited/account/Activities/StartDate=2018-01-01~EndDate=${today}/500`;
  const r = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: { 'accept': 'application/json', 'accept-language': A.lang || 'en-US', 'x-authorization-api': A.xAuth }
  });
  if (r.status !== 200) return JSON.stringify({ error: 'HTTP ' + r.status + ' — token may be stale; re-run capture.' });
  const j = await r.json();
  const acts = (j.data && j.data.activities) || [];
  window.__uact = acts;
  const sum = acts.reduce((s, a) => s + (a.TotalMiles || 0), 0);
  const dates = acts.map(a => a.TransactionDate).sort();
  return JSON.stringify({ count: acts.length, totalMilesSum: sum, oldest: dates[0], newest: dates[dates.length - 1] });
})();
