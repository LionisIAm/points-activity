// TEMPLATE (DOM path) — run in a logged-in <domain> tab via javascript_tool.
// Reads the rendered activity table/list, normalizes rows, stashes them on
// window.__exact, and returns a summary. Keep this file OR fetch_activity.js
// (delete the one you don't use).
//
// Read each ROW container and pull fields from WITHIN it — do NOT zip three
// separate querySelectorAll arrays (a header row causes a one-row shift). Watch for:
//   - Shadow DOM (web components): recurse el.shadowRoot
//   - lazy/accordion sections: click to expand before scraping
//   - "Load more" pagination: click until the row count stabilizes
(() => {
  const norm = (s) => (s || '').trim().replace(/\s+/g, ' ');

  // TODO: find the activity table/rows by a stable signature.
  const tbl = Array.from(document.querySelectorAll('table')).find((t) =>
    t.rows.length > 1 &&
    Array.from(t.rows[0].cells).some((c) => /date/i.test(c.innerText || ''))
  );
  if (!tbl) return JSON.stringify({ error: 'activity table not found' });

  const rows = [];
  for (let i = 1; i < tbl.rows.length; i++) {
    const cells = Array.from(tbl.rows[i].cells).map((c) => norm(c.innerText));
    // TODO: map your real columns; compute kind from the source signal.
    const amount = parseInt((cells[/*amount col*/ 3] || '0').replace(/[+,]/g, ''), 10) || 0;
    rows.push({
      date: cells[/*date col*/ 0],          // TODO: convert to ISO yyyy-mm-dd
      kind: amount < 0 ? 'R' : 'E',          // TODO: your real classifier
      description: cells[/*desc col*/ 1] || '',
      amount
    });
  }

  window.__exact = rows;
  const text = (document.body && document.body.innerText) || '';
  const balMatch = text.match(/([\d,]+)\s*(?:points|miles|avios)/i);  // TODO: tune
  return JSON.stringify({
    count: rows.length,
    totalSum: rows.reduce((s, x) => s + (x.amount || 0), 0),
    balance: balMatch ? parseInt(balMatch[1].replace(/,/g, ''), 10) : null
  });
})();
