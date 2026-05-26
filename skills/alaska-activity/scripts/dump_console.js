// Run after scrape_activity.js. Emits one line per transaction, prefixed AK###~ so
// read_console_messages (pattern ^AK\d) can retrieve them. Columns are '~'-joined:
//   Date~Activity~Status~Points~BonusPoints~TotalPoints~StatusPoints
(() => {
  const rows = window.__akrows || [];
  rows.forEach((c, i) => console.log('AK' + String(i).padStart(3, '0') + '~' + c.join('~')));
  return 'logged ' + rows.length;
})();
