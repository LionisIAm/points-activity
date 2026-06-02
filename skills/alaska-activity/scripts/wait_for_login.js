// Auto-detect Alaska Atmos Rewards login on alaskaair.com. DOM-scraped (Shadow
// DOM). The activity page shows the points balance prominently when logged in.
// Polls every 3 seconds for up to ~4 minutes.
//
// Returns JSON string:
//   {status:"logged-in", waited_s: <int>}  ← good to proceed
//   {status:"timeout"}                     ← user never logged in; ask them
(async () => {
  const MAX_S = 240, INTERVAL_MS = 3000;
  // Walk Shadow DOMs when collecting innerText so balance inside web components
  // counts too — Atmos renders inside Shadow roots.
  const collectText = (root, out) => {
    if (!root) return;
    if (root.innerText) out.push(root.innerText);
    const all = root.querySelectorAll ? root.querySelectorAll('*') : [];
    for (const el of all) if (el.shadowRoot) collectText(el.shadowRoot, out);
  };
  const BAL_RE = /\b\d{1,3}(?:,\d{3})*\s*(miles|points|pts)\b/i;
  const start = Date.now();
  while ((Date.now() - start) / 1000 < MAX_S) {
    try {
      const path = (location.pathname + location.hash).toLowerCase();
      const notLogin = !/sign[-_]?in|log[-_]?in|auth/.test(path);
      const out = []; collectText(document.body, out);
      const hasBalance = BAL_RE.test(out.join('\n'));
      if (notLogin && hasBalance) {
        return JSON.stringify({ status: 'logged-in', waited_s: Math.round((Date.now() - start) / 1000) });
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, INTERVAL_MS));
  }
  return JSON.stringify({ status: 'timeout' });
})();
