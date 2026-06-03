// Qatar Airways Privilege Club activity scraper. Reads the rendered activity
// table on /en/Privilege-Club/postLogin/dashboardqrpcuser/my-activities.html
// and normalizes each row to a flat object on window.__qract.
//
// Output row: { date: 'YYYY-MM-DD', activity, description, company, status, avios }
//   - date is ISO (converted from "DD Month YYYY")
//   - avios is a signed integer (commas stripped, '+'/'-' respected)
//   - Qpoints / Qcredits columns are IGNORED (status-only, not spendable)
//   - status is verbatim ("Completed" or "CANCELLED" — used by transform.py)
//
// Returns JSON string: { count, totalAviosSum, balance }
(() => {
  const MONTHS = {
    january:'01', february:'02', march:'03', april:'04', may:'05', june:'06',
    july:'07', august:'08', september:'09', october:'10', november:'11', december:'12'
  };
  const isoDate = (s) => {
    const m = (s || '').trim().match(/^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/);
    if (!m) return s;
    const dd = m[1].padStart(2, '0');
    const mm = MONTHS[m[2].toLowerCase()] || '00';
    return `${m[3]}-${mm}-${dd}`;
  };
  const parseAvios = (s) => {
    s = (s || '').replace(/,/g, '').trim();
    if (!s || s === '0' || s === '+0' || s === '-0') return 0;
    const m = s.match(/^([+-]?)(\d+)/);
    if (!m) return 0;
    const sign = m[1] === '-' ? -1 : 1;
    return sign * parseInt(m[2], 10);
  };
  const norm = (s) => (s || '').trim().replace(/\s+/g, ' ');

  const tbl = Array.from(document.querySelectorAll('table')).find(t =>
    t.rows.length > 1 &&
    Array.from(t.rows[0].cells).some(c => /transaction date/i.test(c.innerText || ''))
  );
  if (!tbl) return JSON.stringify({ error: 'activity table not found' });

  const headers = Array.from(tbl.rows[0].cells).map(c => norm(c.innerText));
  const idx = {
    date: headers.findIndex(h => /transaction date/i.test(h)),
    activity: headers.findIndex(h => /^activity$/i.test(h)),
    description: headers.findIndex(h => /description/i.test(h)),
    company: headers.findIndex(h => /company/i.test(h)),
    status: headers.findIndex(h => /status/i.test(h)),
    avios: headers.findIndex(h => /avios/i.test(h))
  };

  const rows = [];
  let totalAvios = 0;
  for (let i = 1; i < tbl.rows.length; i++) {
    const cells = Array.from(tbl.rows[i].cells).map(c => norm(c.innerText));
    const av = parseAvios(cells[idx.avios]);
    const row = {
      date: isoDate(cells[idx.date]),
      activity: cells[idx.activity] || '',
      description: cells[idx.description] || '',
      company: cells[idx.company] || '',
      status: cells[idx.status] || '',
      avios: av
    };
    rows.push(row);
    totalAvios += av;
  }
  window.__qract = rows;

  // Balance from page text
  const text = (document.body && document.body.innerText) || '';
  const m = text.match(/(\d{1,3}(?:,\d{3})+)\s+Total balance/i);
  const balance = m ? parseInt(m[1].replace(/,/g, ''), 10) : null;

  return JSON.stringify({ count: rows.length, totalAviosSum: totalAvios, balance });
})();
