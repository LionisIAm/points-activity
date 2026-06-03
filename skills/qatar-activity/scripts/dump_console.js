// Run after scrape_activity.js. Emits one tilde-delimited line per row, prefixed
// QRNNN~ so read_console_messages (pattern ^QR\d) can retrieve them.
// Field order: Date ~~ Activity ~~ Description ~~ Company ~~ Status ~~ Avios
//   - Status: verbatim (e.g. "Completed", "CANCELLED") — transform drops CANCELLED.
//   - Avios is signed.
(() => {
  const rows = window.__qract || [];
  rows.forEach((r, i) => {
    const line = [
      r.date,
      (r.activity || '').replace(/~/g, '-'),
      (r.description || '').replace(/~/g, '-'),
      (r.company || '').replace(/~/g, '-'),
      (r.status || '').replace(/~/g, '-'),
      r.avios
    ].join(' ~~ ');
    console.log('QR' + String(i).padStart(3, '0') + ': ' + line);
  });
  return 'logged ' + rows.length;
})();
