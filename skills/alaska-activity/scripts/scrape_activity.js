// Alaska Atmos Rewards activity scraper — run via javascript_tool (javascript_exec)
// in a logged-in alaskaair.com Atmos Rewards activity tab.
//
// WHY DOM, NOT API: the activity API (apis.alaskaair.com/.../accrueredeemmw/api/
// activities) is "Failed to fetch" from page context — CORS, and the client doesn't
// route it through window.fetch/XHR so it can't be intercepted. The data renders into
// a WEB COMPONENT (Shadow DOM), so we pierce shadow roots and read the table.
//
// PERIOD: the Filters dropdown offers Past 3 / 6 / 12 / 24 months (default 3). 24 is
// the max. Set it, Apply, then click "Show More" until the row count stops growing.
//
// CAPTURE EVERYTHING — STRUCTURAL FILTER, NOT A STATUS WHITELIST:
// a row is a transaction iff its first cell is a date (MM/DD/YYYY) and its Total-points
// cell (index 5) is numeric. We deliberately do NOT filter by status text
// (Credited/Redeemed/Redeposited/...) — a whitelist silently drops any status we didn't
// anticipate (this bit us once with "Redeposited" reversals). Structure is stable;
// status vocabulary is not.
//
// COLUMNS (7): Date | Activity | Status | Points | Bonus points | Total points | Status points
// Only "Total points" (index 5) is the spendable currency. "Status points" (index 6)
// is elite-qualifying and is dropped in transform.
(async () => {
  const txt = el => (el && (el.textContent || '')).trim();

  const findInShadow = (pred) => {
    const out = [];
    const walk = (root) => {
      if (!root || !root.querySelectorAll) return;
      root.querySelectorAll('*').forEach(el => { if (pred(el)) out.push(el); if (el.shadowRoot) walk(el.shadowRoot); });
    };
    walk(document);
    return out;
  };

  // 1. open Filters, choose "Past 24 Months", Apply
  const filterField = findInShadow(el => el.children.length === 0 && /no filters applied|filters/i.test(txt(el)))[0];
  if (filterField) { (filterField.closest('button,[role="button"],div') || filterField).click(); await new Promise(r => setTimeout(r, 800)); }
  const opt24 = findInShadow(el => el.children.length === 0 && /past 24 months/i.test(txt(el)))[0];
  if (opt24) { (opt24.closest('label,[role="radio"],button,div') || opt24).click(); await new Promise(r => setTimeout(r, 400)); }
  const applyBtn = findInShadow(el => (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') && /apply/i.test(txt(el)))[0];
  if (applyBtn) { applyBtn.click(); await new Promise(r => setTimeout(r, 2500)); }

  // 2. structural row counter (date + numeric Total)
  const collect = () => {
    const seen = new Set(); const data = [];
    const walk = (root) => {
      if (!root || !root.querySelectorAll) return;
      root.querySelectorAll('*').forEach(el => { if (el.shadowRoot) walk(el.shadowRoot); });
      root.querySelectorAll('tr,[class*="row"],[role="row"]').forEach(r => {
        const cells = [...r.children].map(c => c.textContent.trim().replace(/\s+/g, ' '));
        if (cells.length < 7) return;
        if (!/^\d{2}\/\d{2}\/\d{4}$/.test(cells[0])) return;       // must start with a date
        if (!/^-?[\d,]+$/.test((cells[5] || '').trim())) return;   // Total points must be numeric
        const key = cells.join('|').slice(0, 90);
        if (!seen.has(key)) { seen.add(key); data.push(cells); }
      });
    };
    walk(document);
    return data;
  };

  // 3. click "Show More" until row count stabilizes
  let last = collect().length;
  for (let i = 0; i < 40; i++) {
    const sm = findInShadow(el => (el.tagName === 'BUTTON' || el.tagName === 'A') && /show more/i.test(txt(el)));
    if (!sm.length) break;
    sm[0].scrollIntoView({ block: 'center' }); sm[0].click();
    await new Promise(r => setTimeout(r, 1500));
    const now = collect().length;
    if (now === last) break;
    last = now;
  }

  const rows = collect();
  window.__akrows = rows;
  return JSON.stringify({ count: rows.length, oldest: rows.length ? rows[rows.length - 1][0] : null, newest: rows.length ? rows[0][0] : null });
})();
