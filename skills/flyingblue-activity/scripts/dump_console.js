// Run after fetch_activity.js. Emits one tilde-delimited line per flattened row,
// prefixed FBNNN~ so read_console_messages (pattern ^FB\d) can retrieve them.
// Field order: Date ~~ Kind ~~ Description ~~ Miles
// (Kind: 'E' = earn, 'R' = redeem. Miles is signed.)
(() => {
  const rows = window.__fbact || [];
  rows.forEach((r, i) => {
    const line = [r.date, r.kind, (r.description || '').replace(/~/g, '-'), r.miles].join(' ~~ ');
    console.log('FB' + String(i).padStart(3, '0') + ': ' + line);
  });
  return 'logged ' + rows.length;
})();
