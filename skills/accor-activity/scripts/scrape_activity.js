// Accor (ALL) account points-statement scraper — run via javascript_tool
// (javascript_exec) in a logged-in all.accor.com transaction-history tab.
// Expands every collapsed year accordion, then reads each table row, keeping the
// year context. Stashes rows on window.__accor; dump to console with the next
// script and read back via read_console_messages.
//
// WHY DOM, NOT API: Accor's data lives behind api.accor.com (Bearer JWT in
// localStorage['identification-token_all.accor'] + apiKey + x-caller headers). Auth
// can be reconstructed, but the points-statement endpoint itself never appears in
// network logs or fetch/XHR hooks (data is delivered at first render and cached in
// the Angular state; /orders/me/orders returns only bookings, not point lines). The
// rendered table is complete and the reward-points sum reconciles to the balance, so
// scraping is the reliable path.
//
// PAGE STRUCTURE: history is grouped into year accordions
// (.transaction-history-by-year). The current year is expanded; older years are
// COLLAPSED and their rows are NOT in the DOM until you click the year header. Each
// row is <tr class="simple-grid__tr--tbody"> with 5 <td>: Description, Date
// (MM/DD/YYYY), Reward points, Status points, Nights. Empty cell = "-".
(async () => {
  // 1. expand every collapsed year by clicking its header row
  const yearBlocks = () => [...document.querySelectorAll('.transaction-history-by-year')];
  for (let pass = 0; pass < 12; pass++) {
    let clicked = false;
    for (const b of yearBlocks()) {
      const hasRows = b.querySelectorAll('tr.simple-grid__tr--tbody').length > 0;
      if (!hasRows) {
        // click the year header (the recap/header element) to expand
        const header = b.querySelector('[class*="year"], [class*="recap"], [class*="header"]') || b;
        header.click();
        clicked = true;
        await new Promise(r => setTimeout(r, 1200));
      }
    }
    if (!clicked) break;
  }
  // 2. parse rows per year block (keep year context)
  const out = [];
  for (const b of yearBlocks()) {
    const yr = (b.textContent.match(/20\d\d/) || [])[0] || '';
    for (const tr of b.querySelectorAll('tr.simple-grid__tr--tbody')) {
      const tds = [...tr.querySelectorAll('td')].map(td => td.textContent.trim());
      // tds: [desc, date, reward, status, nights]
      out.push([yr, ...tds]);
    }
  }
  window.__accor = out;
  return JSON.stringify({ count: out.length, years: [...new Set(out.map(r => r[0]))] });
})();
