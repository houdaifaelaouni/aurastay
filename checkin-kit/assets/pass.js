/* Builds the check-in pass PDF. Needs jsPDF (window.jspdf) and qrcode-generator (window.qrcode). */
(function () {
  const hex = h => { const n = parseInt(String(h || '#1d3b33').replace('#', ''), 16); return [n >> 16 & 255, n >> 8 & 255, n & 255]; };
  const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  const day = v => new Date(v + 'T12:00:00');
  const fmt = (v, o) => day(v).toLocaleDateString('en-GB', o);
  const nights = (a, b) => Math.round((day(b) - day(a)) / 864e5);

  // Letter-spaced label; jsPDF's align ignores char spacing, so right-align by hand.
  function label(doc, text, x, y, cs, align) {
    doc.setCharSpace(cs);
    const w = doc.getTextWidth(text) + cs * (text.length - 1);
    doc.text(text, align === 'right' ? x - w : x, y);
    doc.setCharSpace(0);
  }

  function buildPass(d) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: 'mm', format: 'a4' });
    const W = 210, H = 297, M = 18;
    const brand = hex(d.brand), ink = [22, 27, 25], muted = [112, 119, 115], line = [228, 230, 226];
    const tint = mix(brand, [255, 255, 255], 0.92), gold = [200, 169, 106];
    doc.setProperties({ title: `Check-in pass ${d.reference}`, author: d.agency || 'Check-in pass', subject: d.property });

    // Header band
    doc.setFillColor(...brand); doc.rect(0, 0, W, 64, 'F');
    doc.setFillColor(...mix(brand, [0, 0, 0], 0.18)); doc.rect(0, 60, W, 4, 'F');
    doc.setTextColor(...gold); doc.setFont('helvetica', 'bold'); doc.setFontSize(8);
    label(doc, 'CHECK-IN PASS', M, 20, 1.6);
    doc.setTextColor(255, 255, 255); doc.setFontSize(22);
    doc.text(doc.splitTextToSize(d.agency || 'Welcome', 110)[0], M, 31);
    doc.setFont('helvetica', 'normal'); doc.setFontSize(10); doc.setTextColor(...mix([255, 255, 255], brand, 0.3));
    doc.text(`Welcome, ${d.guest.split(' ')[0]}. We look forward to hosting you.`, M, 39);
    doc.setFontSize(7.5); doc.setTextColor(...mix([255, 255, 255], brand, 0.35));
    label(doc, 'BOOKING REFERENCE', W - M, 20, 1.2, 'right');
    doc.setFont('helvetica', 'bold'); doc.setFontSize(15); doc.setTextColor(255, 255, 255);
    doc.text(d.reference, W - M, 28, { align: 'right' });
    doc.setFont('helvetica', 'normal'); doc.setFontSize(8.5); doc.setTextColor(...mix([255, 255, 255], brand, 0.3));
    [d.agencyPhone, d.agencyEmail].filter(Boolean).forEach((t, i) => doc.text(t, W - M, 35 + i * 4.6, { align: 'right' }));

    // Stay card overlapping the header
    const cy = 48, ch = 58;
    doc.setFillColor(0, 0, 0); doc.setGState(new doc.GState({ opacity: 0.06 })); doc.roundedRect(M + 0.6, cy + 1.2, W - 2 * M, ch, 3, 3, 'F');
    doc.setGState(new doc.GState({ opacity: 1 }));
    doc.setFillColor(255, 255, 255); doc.setDrawColor(...line); doc.roundedRect(M, cy, W - 2 * M, ch, 3, 3, 'FD');
    doc.setTextColor(...ink); doc.setFont('helvetica', 'bold'); doc.setFontSize(15);
    doc.text(doc.splitTextToSize(d.property, W - 2 * M - 16)[0], M + 8, cy + 12);
    doc.setFont('helvetica', 'normal'); doc.setFontSize(9); doc.setTextColor(...muted);
    if (d.address) doc.text(doc.splitTextToSize(d.address, W - 2 * M - 16)[0], M + 8, cy + 18.5);
    doc.setDrawColor(...line); doc.line(M + 8, cy + 25, W - M - 8, cy + 25);
    const col = (x, name, big, small) => {
      doc.setFont('helvetica', 'bold'); doc.setFontSize(6.8); doc.setTextColor(...muted); label(doc, name, x, cy + 33, 1);
      doc.setTextColor(...ink); doc.setFontSize(17); doc.text(big, x, cy + 42);
      doc.setFont('helvetica', 'normal'); doc.setFontSize(8.5); doc.setTextColor(...muted); doc.text(small, x, cy + 48);
    };
    const n = nights(d.checkin, d.checkout);
    col(M + 8, 'CHECK-IN', fmt(d.checkin, { day: '2-digit', month: 'short' }), fmt(d.checkin, { weekday: 'long' }) + (d.checkinTime ? ` · from ${d.checkinTime}` : ''));
    doc.setDrawColor(...brand); doc.setLineWidth(0.5); doc.line(M + 58, cy + 39, M + 68, cy + 39); doc.line(M + 66, cy + 37, M + 68, cy + 39); doc.line(M + 66, cy + 41, M + 68, cy + 39); doc.setLineWidth(0.2);
    col(M + 76, 'CHECK-OUT', fmt(d.checkout, { day: '2-digit', month: 'short' }), fmt(d.checkout, { weekday: 'long' }) + (d.checkoutTime ? ` · by ${d.checkoutTime}` : ''));
    col(M + 128, 'NIGHTS', String(n), fmt(d.checkin, { year: 'numeric' }));
    col(M + 152, 'GUESTS', String(d.guests), Number(d.guests) === 1 ? 'guest' : 'guests');

    // Guest details (left) + QR card (right)
    const ty = cy + ch + 13, qs = 52, qx = W - M - qs - 8, qy = ty + 6;
    doc.setFont('helvetica', 'bold'); doc.setFontSize(7); doc.setTextColor(...brand); label(doc, 'GUEST DETAILS', M, ty, 1.4);
    let y = ty + 10;
    for (const [k, v] of [['Name', d.guest], ['Email', d.email], ['Phone', d.phone], ['Dates', `${fmt(d.checkin, { day: 'numeric', month: 'long', year: 'numeric' })} – ${fmt(d.checkout, { day: 'numeric', month: 'long', year: 'numeric' })}`]]) {
      if (!v) continue;
      doc.setFont('helvetica', 'normal'); doc.setFontSize(8.5); doc.setTextColor(...muted); doc.text(k, M, y);
      doc.setFont('helvetica', 'bold'); doc.setFontSize(10.5); doc.setTextColor(...ink); doc.text(doc.splitTextToSize(v, qx - M - 40)[0], M + 22, y);
      doc.setDrawColor(...line); doc.line(M, y + 4, qx - 14, y + 4); y += 11.5;
    }
    doc.setFillColor(...tint); doc.roundedRect(qx - 8, ty - 6, qs + 16, qs + 32, 3, 3, 'F');
    doc.setFillColor(255, 255, 255); doc.roundedRect(qx - 3, qy - 3, qs + 6, qs + 6, 2, 2, 'F');
    const qr = qrcode(0, 'M'); qr.addData(d.qrText); qr.make();
    const m = qr.getModuleCount(), cell = qs / m; doc.setFillColor(...ink);
    for (let r = 0; r < m; r++) for (let c = 0; c < m; c++) if (qr.isDark(r, c)) doc.rect(qx + c * cell, qy + r * cell, cell + 0.03, cell + 0.03, 'F');
    doc.setFont('helvetica', 'bold'); doc.setFontSize(8); doc.setTextColor(...brand); doc.text('SCAN ON ARRIVAL', qx + qs / 2, qy + qs + 9, { align: 'center' });
    doc.setFont('courier', 'bold'); doc.setFontSize(12); doc.setTextColor(...ink); doc.text(d.code.replace(/(.{5})/, '$1 '), qx + qs / 2, qy + qs + 15.5, { align: 'center' });

    // Perforation
    const py = Math.max(y, ty - 6 + qs + 32) + 8;
    doc.setFillColor(243, 244, 241); doc.circle(0, py, 5, 'F'); doc.circle(W, py, 5, 'F');
    doc.setDrawColor(200, 204, 198); doc.setLineDashPattern([1.5, 1.5], 0); doc.line(8, py, W - 8, py); doc.setLineDashPattern([], 0);

    // Notes + host
    y = py + 10;
    if (d.notes) {
      doc.setFont('helvetica', 'normal'); doc.setFontSize(9.5);
      const lines = doc.splitTextToSize(d.notes, W - 2 * M - 16).slice(0, 11), h = lines.length * 4.6 + 16;
      doc.setFillColor(...tint); doc.roundedRect(M, y, W - 2 * M, h, 3, 3, 'F');
      doc.setFillColor(...brand); doc.rect(M, y, 1.4, h, 'F');
      doc.setFont('helvetica', 'bold'); doc.setFontSize(10.5); doc.setTextColor(...ink); doc.text('Good to know', M + 8, y + 8);
      doc.setFont('helvetica', 'normal'); doc.setFontSize(9.5); doc.setTextColor(62, 70, 66); doc.text(lines, M + 8, y + 14.5);
      y += h + 10;
    }
    // Footer
    doc.setDrawColor(...line); doc.line(M, H - 20, W - M, H - 20);
    doc.setFontSize(7.5); doc.setTextColor(...muted);
    doc.text('This pass is personal and valid for one check-in. Please have an ID ready on arrival.', M, H - 13);
    doc.text('Issued ' + new Date().toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }), W - M, H - 13, { align: 'right' });
    return doc;
  }
  window.buildPass = buildPass;
})();
