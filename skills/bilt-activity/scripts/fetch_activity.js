// Bilt Rewards activity fetcher — run via javascript_tool (javascript_exec) in a
// logged-in bilt.com tab (e.g. https://www.bilt.com/rewards/activity).
//
// API: GET https://api.biltrewards.com/loyalty/activity?month=M&year=Y
//   header: authorization: Bearer <jwt>   (jwt lives in localStorage)
// Plain fetch with credentials works. ONLY month+year filter — limit/page/from/to/
// startDate are all ignored (return the default ~12 recent rows). So we iterate months
// backward from the current month until we hit 3 consecutive empty months.
// Bilt has NO history-window limit (unlike Alaska/Aeroplan): full account history is
// retrievable, and sum(totalPoints) reconciles to the displayed balance.
//
// Entry shape we keep (compacted): {d:YYYY-MM-DD, t:title, a:activity, s:pointState,
//   tp:totalPoints int, b:[{t:benefitTitle, v:points int}]}. Only point-bearing
//   benefit items are kept (cash-back "Earn Bilt Cash" / non-point benefits dropped).
//   Verified: sum(b[].v) == tp for every entry.
(async () => {
  // 1. find the bearer token in localStorage (a long JWT starting with "ey")
  let tok = null;
  for (let i = 0; i < localStorage.length; i++) {
    const v = localStorage.getItem(localStorage.key(i));
    if (/^ey/.test(v) && v.length > 200) { tok = 'Bearer ' + v; break; }
    try {
      const m = JSON.stringify(JSON.parse(v))
        .match(/ey[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}/);
      if (m) { tok = 'Bearer ' + m[0]; break; }
    } catch (e) {}
  }
  if (!tok) return JSON.stringify({ error: 'no auth token found in localStorage — is the user logged in?' });

  const H = { accept: 'application/json', authorization: tok };
  const pv = (v) => {                    // parse a benefit value like "+95" / "-9,000"; skip "$" (cash)
    if (typeof v !== 'string') return null;
    if (v.indexOf('$') !== -1) return null;
    const n = parseInt(v.replace(/[+,]/g, ''));
    return isNaN(n) ? null : n;
  };

  const now = new Date();
  let y = now.getUTCFullYear(), m = now.getUTCMonth() + 1;
  const all = []; let emptyStreak = 0;
  for (let i = 0; i < 60; i++) {         // hard cap 60 months
    const r = await fetch(`https://api.biltrewards.com/loyalty/activity?month=${m}&year=${y}`,
                          { headers: H, credentials: 'include' });
    let n = 0;
    if (r.ok) {
      const j = await r.json();
      const entries = j.entries || [];
      n = entries.length;
      for (const e of entries) {
        all.push({
          d: (e.datetime || '').slice(0, 10),
          t: e.title,
          a: e.activity || '',
          s: e.pointState || '',
          tp: e.totalPoints || 0,
          b: (e.benefits || []).map(bn => ({ t: bn.title, v: pv(bn.value) })).filter(bn => bn.v !== null)
        });
      }
    }
    emptyStreak = n === 0 ? emptyStreak + 1 : 0;
    if (emptyStreak >= 3) break;         // assume history ended
    m--; if (m === 0) { m = 12; y--; }
  }

  window.__biltall = all;
  return JSON.stringify({
    count: all.length,
    oldest: all.length ? all[all.length - 1].d : null,
    newest: all.length ? all[0].d : null,
    balanceCheck: all.reduce((a, e) => a + (e.tp || 0), 0)   // should equal displayed balance
  });
})();
