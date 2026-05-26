// Run after scrape_activity.js. Emits each row as a tilde-delimited console line
// prefixed ACNNN~ so read_console_messages (pattern ^AC\d) can retrieve them.
// Field order: year ~~ description ~~ date ~~ reward ~~ status ~~ nights
// (reward/status/nights keep their "+ "/"- "/"-" form — cleaned in transform).
(() => {
  const rows = window.__accor || [];
  rows.forEach((r, i) => {
    console.log('AC' + String(i).padStart(3, '0') + ': ' + r.join(' ~~ '));
  });
  return 'logged ' + rows.length;
})();
