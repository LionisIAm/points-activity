// Run after scrape_activity.js. Emits one tilde-delimited line per row,
// prefixed HHNNN~ so read_console_messages (pattern ^HH\d) can retrieve them.
// Field order: Date ~~ Kind ~~ Description ~~ Confirmation ~~ Points
//   - Kind: 'earn' (Points earned) or 'refund' (Points refunded). Both are
//     positive credits to the account.
//   - Points is the unsigned integer Hilton displays.
(() => {
  const rows = window.__hhact || [];
  rows.forEach((r, i) => {
    const line = [
      r.date,
      r.kind || 'earn',
      (r.desc || '').replace(/~/g, '-'),
      (r.confirmation || '').replace(/~/g, '-'),
      r.points || 0
    ].join(' ~~ ');
    console.log('HH' + String(i).padStart(3, '0') + ': ' + line);
  });
  return 'logged ' + rows.length;
})();
