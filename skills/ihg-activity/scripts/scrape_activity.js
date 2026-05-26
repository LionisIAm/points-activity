// IHG account-activity scraper — run via javascript_tool (javascript_exec) in a
// logged-in ihg.com activity tab. Scrolls to load all rows, then reads each table
// row. Stashes rows on window.__ihg; emit to console with dump (next script) and
// read back via read_console_messages (raw return is often blocked by the chat).
//
// WHY DOM, NOT API: IHG's data API (apis.ihg.com/members/v1/profiles/me/activities)
// requires an apikey + X-IHG-SSO-TOKEN header set that a plain fetch can't reliably
// reproduce (returns 504). The activity page only ever shows ~365 days / ~30 rows
// anyway, and that IS the full available history — so scraping the rendered table
// is sufficient and simpler.
//
// PARSING NOTE: read each field from WITHIN one <tr> (date-wrap, detail-wrap,
// note-t-black). Do NOT build three separate querySelectorAll arrays and zip them —
// the header row offsets the counts and you'll get a one-row shift.
(async () => {
  // 1. scroll to force lazy-load of all rows
  let last = 0;
  for (let i = 0; i < 15; i++) {
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, 900));
    const n = document.querySelectorAll('.date-wrap').length;
    if (n === last && n > 1) break;
    last = n;
  }
  // 2. parse per-row
  const trs = [...document.querySelectorAll('tr')].filter(tr => {
    try { const d = tr.querySelector('.date-wrap'); return d && /\d{2}\/\d{2}\/\d{4}/.test(d.textContent); }
    catch (e) { return false; }
  });
  const rows = [];
  for (const tr of trs) {
    const date = tr.querySelector('.date-wrap').textContent.trim();
    const detEl = tr.querySelector('.detail-wrap');
    let desc = '';
    if (detEl) {
      const parts = [...detEl.querySelectorAll('*')]
        .filter(e => e.children.length === 0 && e.textContent.trim())
        .map(e => e.textContent.trim());
      desc = parts.length ? [...new Set(parts)].join(' | ') : detEl.textContent.trim();
    }
    const note = tr.querySelector('.note-t-black');
    const pts = note ? note.textContent.trim() : '';
    rows.push([date, desc, pts]);
  }
  window.__ihg = rows;
  return JSON.stringify({ count: rows.length, newest: rows[0] && rows[0][0], oldest: rows[rows.length - 1] && rows[rows.length - 1][0] });
})();
