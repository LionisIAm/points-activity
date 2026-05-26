// Run after fetch_activity.js. Emits the collected entries as a JSON array, chunked and
// prefixed BILT###~ so read_console_messages(pattern "^BILT\\d") can retrieve them.
// Reassemble the chunks in order, concatenate the arrays, and write to raw.json for
// transform.py. (Chunked because a single console line can exceed capture limits.)
(() => {
  const all = window.__biltall || [];
  const CHUNK = 40;
  let idx = 0;
  for (let i = 0; i < all.length; i += CHUNK) {
    console.log('BILT' + String(idx).padStart(3, '0') + '~' + JSON.stringify(all.slice(i, i + CHUNK)));
    idx++;
  }
  return JSON.stringify({ chunks: idx, total: all.length, perChunk: CHUNK });
})();
