// Run after scrape_activity.js. Emits one line per transaction, prefixed AENNN~ so
// read_console_messages (pattern ^AE\d) can retrieve them. The header text is already
// pipe-joined as: MONTH|DD|YYYY|Partner|Description|±N Pts
(() => {
  const rows = window.__aero || [];
  rows.forEach((r, i) => console.log('AE' + String(i).padStart(3, '0') + ': ' + r));
  return 'logged ' + rows.length;
})();
