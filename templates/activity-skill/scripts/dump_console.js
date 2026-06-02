// TEMPLATE — run after fetch_activity.js / scrape_activity.js. Emits one
// tilde-delimited line per row, prefixed XX###: so read_console_messages
// (pattern ^XX\d) can retrieve them. Choose a UNIQUE 2-letter prefix per program
// (e.g. HX Hyatt, UA United, FB Flying Blue) so patterns don't collide.
// Field order MUST match what transform.py parses: Date ~~ Kind ~~ Description ~~ Amount
(() => {
  const rows = window.__exact || [];
  rows.forEach((r, i) => {
    const line = [r.date, r.kind, (r.description || '').replace(/~/g, '-'), r.amount].join(' ~~ ');
    console.log('XX' + String(i).padStart(3, '0') + ': ' + line);
  });
  return 'logged ' + rows.length;
})();
