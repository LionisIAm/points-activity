// Run after fetch_activity.js. Emits each transaction as one tilde-delimited
// console line prefixed HXNNN~, so read_console_messages (pattern ^HX\d) can
// retrieve them. Tilde delimiter avoids commas in hotel names / descriptions.
// Field order: date~category~pointsType~baseAmount~totalAmount~qualifyingNights~name~bonusDetail
// bonusDetail is "Label=amount; Label=amount" (the nested point-bearing components).
(() => {
  const u = window.__hyattRows || [];
  u.forEach((x, i) => {
    const t = x.transaction;
    const bonus = (x.bonusDetail || []).map(b => `${b.description}=${b.amount}`).join('; ');
    const name = (x.hotelDetail && x.hotelDetail.name) || (x.misc && x.misc.description) || '';
    const line = [t.date, t.category.replace('TRXN_', ''), t.pointsType,
                  t.baseAmount, t.totalAmount, t.qualifyingNights, name, bonus].join('~');
    console.log('HX' + String(i).padStart(3, '0') + '~' + line);
  });
  return 'logged ' + u.length;
})();
