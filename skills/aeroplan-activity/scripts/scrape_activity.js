// Air Canada Aeroplan activity scraper — run via javascript_tool (javascript_exec)
// in a logged-in aircanada.com Aeroplan activity tab. Sets the period filter to its
// max (2 years), loads all transaction panels, and reads each one. Stashes rows on
// window.__aero; dump to console with the next script and read back via
// read_console_messages.
//
// WHY DOM, NOT API: activity is served by an AWS AppSync GraphQL endpoint
// (akamai-gw.dbaas.aircanada.com/appsync/transaction-history-v2). A plain fetch
// fails (CORS / needs the Amplify client's auth), and the real request doesn't go
// through window.fetch/XHR so it can't be intercepted. The data renders into the
// normal light DOM (Angular Material mat-expansion-panel), so scraping is reliable.
//
// PAGE STRUCTURE: each transaction is a <mat-expansion-panel>; its header has
// MONTH / DD / YYYY, partner (e.g. "Air Canada", "American Express US"),
// description (often with a Booking Reference), and a "±N Pts" amount. Some panels
// are ADS (e.g. "Earn points with Starbucks") with no "Pts" — skip those. Expanding a
// panel shows a your-balance / other-pool-member split; we IGNORE that and take only
// the header total.
//
// FAMILY SHARING CAVEAT: if the account is a Family Sharing pool LEAD, the visible
// balance includes other members, but this activity list shows only THIS account's
// transactions — other members' earns/transfers/returns are not here. So the activity
// is inherently incomplete for a pool; do not try to reconcile to the balance.
//
// MAX PERIOD: the Filters panel offers 30/60/90 days, 6 months, 1 year, 2 years.
// 2 years is the maximum available — older history simply isn't retrievable.
(async () => {
  const txt = el => (el && (el.textContent || '')).trim();

  // 1. open Filters, pick "2 years", apply
  const click = pred => { const el = [...document.querySelectorAll('button,a,label,[role="radio"],mat-radio-button,[role="option"]')].find(pred); if (el) { el.click(); return true; } return false; };
  click(b => /^filters$|filter button/i.test(txt(b) || b.getAttribute('aria-label') || ''));
  await new Promise(r => setTimeout(r, 1200));
  const opt = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && /^2 years$/i.test(txt(e)));
  if (opt) (opt.closest('button,label,[role="radio"],[role="option"],mat-radio-button') || opt).click();
  await new Promise(r => setTimeout(r, 600));
  click(b => /^apply( changes)?$/i.test(txt(b)));
  await new Promise(r => setTimeout(r, 2500));

  // 2. click any "More"/"Load more" until the real-transaction count stops growing
  const realCount = () => [...document.querySelectorAll('mat-expansion-panel')].filter(p => /[+\-][\d,]+\s*Pts/i.test(p.innerText || '')).length;
  let last = realCount();
  for (let i = 0; i < 25; i++) {
    const more = [...document.querySelectorAll('button,a')].find(b => /^(more|show more|load more|view more)$/i.test(txt(b)));
    if (!more) break;
    more.scrollIntoView({ block: 'center' }); more.click();
    await new Promise(r => setTimeout(r, 1800));
    const now = realCount();
    if (now === last) break;
    last = now;
  }

  // 3. parse each real transaction panel (skip ad panels with no Pts)
  const rows = [];
  for (const p of document.querySelectorAll('mat-expansion-panel')) {
    if (!/[+\-][\d,]+\s*Pts/i.test(p.innerText || '')) continue;
    const hdr = p.querySelector('mat-expansion-panel-header') || p;
    rows.push(hdr.innerText.replace(/\s*\n\s*/g, '|').replace(/\|+/g, '|').trim());
  }
  window.__aero = rows;
  return JSON.stringify({ count: rows.length });
})();
