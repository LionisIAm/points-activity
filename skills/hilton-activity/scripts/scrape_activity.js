// Hilton Honors activity scraper. Reads the rendered activity list, walks
// through pagination ("Next Page" button), and flattens into one row per
// transaction on window.__hhact.
//
// Output row: { date: 'YYYY-MM-DD', desc, confirmation, kind, points }
//   - date  : ISO start-date of the row
//   - desc  : hotel name (for stays) or activity label (for card spends, etc.)
//   - confirmation : 'Confirmation # XXX' (earn) or 'Cancellation # XXX' (refund), or ''
//   - kind  : 'earn' (Points earned) or 'refund' (Points refunded)
//   - points: signed integer (positive; commas stripped)
//
// Strategy: rely on the rendered text — Hilton's grid has consistent labels
// "Points earned" / "Points refunded" preceded by the amount and (for stays)
// a confirmation marker. We split by these labels then walk back through the
// row text to recover the date + description.
(async () => {
  const MONTHS = {
    january:'01', february:'02', march:'03', april:'04', may:'05', june:'06',
    july:'07', august:'08', september:'09', october:'10', november:'11', december:'12'
  };
  const isoFromDateRangeHeader = (s) => {
    // "September 18, 2025 through September 23, 2025 for 5 nights"
    const m = s.match(/^([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})\s+through/);
    if (!m) return null;
    const mm = MONTHS[m[1].toLowerCase()] || '00';
    return `${m[3]}-${mm}-${m[2].padStart(2, '0')}`;
  };
  const parsePoints = (s) => {
    if (!s) return 0;
    s = s.replace(/,/g, '').replace(/\+/g, '').trim();
    const m = s.match(/^(\d+)/);
    return m ? parseInt(m[1], 10) : 0;
  };

  // Find the page-2-button (if any) and the "Next Page" once
  const findNextButton = () =>
    Array.from(document.querySelectorAll('button')).find(b => /next page/i.test((b.textContent || '').trim()));
  const getResultsRange = () => {
    const t = (document.body && document.body.innerText) || '';
    const m = t.match(/Results\s+(\d+)-(\d+)\s+of\s+(\d+)/i);
    return m ? { from: +m[1], to: +m[2], total: +m[3] } : null;
  };

  // Parse rows from current DOM, using the text-block between "Previous activity"
  // and the page footer. Each row contains a date-range header line plus the
  // "Points earned"/"Points refunded" amount.
  const parseCurrentPage = () => {
    const fullText = (document.body && document.body.innerText) || '';
    const startIdx = fullText.toLowerCase().indexOf('previous activity');
    if (startIdx < 0) return [];
    // Cut at "Page X of N" or end of body
    let endIdx = fullText.indexOf('Page 1 of', startIdx);
    const pe = fullText.indexOf('Page 2 of', startIdx);
    if (pe > 0 && (endIdx < 0 || pe < endIdx)) endIdx = pe;
    const region = fullText.slice(startIdx, endIdx > 0 ? endIdx : fullText.length);
    // Split on the date-range header pattern at line starts
    const lines = region.split('\n');
    const rows = [];
    let current = null;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const drm = line.match(/^([A-Za-z]+\s+\d{1,2},\s+\d{4})\s+through\s+/);
      if (drm) {
        if (current) rows.push(current);
        current = { headerLine: line, date: isoFromDateRangeHeader(line), buffer: [] };
        continue;
      }
      if (current) current.buffer.push(line);
    }
    if (current) rows.push(current);

    // From each row buffer, extract: desc, confirmation, kind, points
    const out = [];
    for (const r of rows) {
      const buf = r.buffer;
      let kind = null, points = 0, descLines = [], confirmation = '';
      for (let i = 0; i < buf.length; i++) {
        const t = buf[i];
        if (/^Points earned$/i.test(t)) {
          kind = 'earn';
          // amount is on the next non-empty line
          for (let j = i + 1; j < buf.length; j++) {
            if (buf[j].trim()) { points = parsePoints(buf[j]); break; }
          }
          break;
        }
        if (/^Points refunded$/i.test(t)) {
          kind = 'refund';
          for (let j = i + 1; j < buf.length; j++) {
            if (buf[j].trim()) { points = parsePoints(buf[j]); break; }
          }
          break;
        }
        // Skip date-cell noise: "13", "MAY", "WED", and "N nights"
        if (/^\d{1,2}$/.test(t)) continue;
        if (/^[A-Z]{3}$/.test(t) && t.length === 3) continue;
        if (/^\d+\s*nights?$/i.test(t)) continue;
        if (/^(Confirmation|Cancellation)\s*#/i.test(t)) {
          confirmation = t;
          continue;
        }
        if (t) descLines.push(t);
      }
      // Description = the most likely activity name. For stays, it's the hotel
      // name (often the line right before "Confirmation # ..."). For card
      // spends, it's just the activity label.
      let desc = descLines.find(l => l.length > 3) || '';
      if (kind === 'refund' && confirmation) {
        // Mark refund descriptively
        desc = `Refund - ${desc}`.replace(/\s+/g, ' ').trim();
      }
      out.push({
        date: r.date,
        desc,
        confirmation,
        kind: kind || 'earn',
        points
      });
    }
    return out;
  };

  // Walk pages
  const all = [];
  const seenSig = new Set();
  let safety = 10;
  while (safety-- > 0) {
    const page = parseCurrentPage();
    for (const row of page) {
      const sig = `${row.date}|${row.desc}|${row.confirmation}|${row.points}|${row.kind}`;
      if (!seenSig.has(sig)) {
        seenSig.add(sig);
        all.push(row);
      }
    }
    const range = getResultsRange();
    if (!range) break;
    if (range.to >= range.total) break;
    const next = findNextButton();
    if (!next || next.disabled) break;
    next.click();
    // Wait for results-counter to advance
    const beforeFrom = range.from;
    let waited = 0;
    while (waited < 8000) {
      await new Promise(r => setTimeout(r, 500));
      waited += 500;
      const r2 = getResultsRange();
      if (r2 && r2.from > beforeFrom) break;
    }
  }

  window.__hhact = all;
  const text = (document.body && document.body.innerText) || '';
  const balMatch = text.match(/([\d,]+)\s*Total Points/);
  const balance = balMatch ? parseInt(balMatch[1].replace(/,/g, ''), 10) : null;
  const totalSum = all.reduce((s, r) => s + (r.points || 0), 0);
  const dates = all.map(r => r.date).filter(Boolean).sort();
  return JSON.stringify({
    count: all.length,
    totalPointsSum: totalSum,
    balance,
    oldest: dates[0] || null,
    newest: dates[dates.length - 1] || null
  });
})();
