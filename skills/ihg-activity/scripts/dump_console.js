// Run after scrape_activity.js. Emits each row as one tilde-delimited console line
// prefixed IXNNN~ so read_console_messages (pattern ^IX\d) can retrieve them.
// Field order: date~~description~~points  (points still has commas/" pts" — cleaned in transform).
(() => {
  const rows = window.__ihg || [];
  rows.forEach((r, i) => {
    console.log('IX' + String(i).padStart(3, '0') + ': ' + r.join(' ~~ '));
  });
  return 'logged ' + rows.length;
})();
