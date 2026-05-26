// Run after fetch_activity.js. Emits one tilde-delimited line per activity, prefixed
// UANNN~ so read_console_messages (pattern ^UA\d) can retrieve them.
// Field order: TransactionDate ~~ ActivityType ~~ Description ~~ TotalMiles ~~ IsRedeposit
// (ActivityType: 'F' = flight, 'O' = other/earning. TotalMiles is the final amount.)
(() => {
  const acts = window.__uact || [];
  acts.forEach((a, i) => {
    const date = (a.TransactionDate || '').slice(0, 10);   // ISO -> YYYY-MM-DD
    const line = [date, a.ActivityType, (a.Description || '').replace(/~/g, '-'), a.TotalMiles, a.IsRedeposit].join(' ~~ ');
    console.log('UA' + String(i).padStart(3, '0') + ': ' + line);
  });
  return 'logged ' + acts.length;
})();
