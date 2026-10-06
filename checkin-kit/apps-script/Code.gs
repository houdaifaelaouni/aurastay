/**
 * Check-in passes: Google Sheet + verify page.
 * Paste into Extensions > Apps Script of your Google Sheet, run setup() once,
 * then Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
 * The generator (create) and the Netlify verify page (lookup, confirm) both POST JSON here.
 */
const API_KEY = 'change-me-long-random-key';  // pasted into the generator; lets it add passes
const STAFF_PIN = '2468';                      // staff type this to confirm a check-in
const SHEET_NAME = 'Checkins';
const HEADERS = ['Code', 'Reference', 'Guest', 'Email', 'Phone', 'Guests', 'Property', 'Address',
  'Check-in', 'Check-out', 'Notes', 'Created at', 'Status', 'Checked in at', 'Checked in by'];

function setup() {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight('bold');
  sheet.setFrozenRows(1);
  sheet.getRange('A:A').setNumberFormat('@');
  sheet.getRange('I:J').setNumberFormat('@');
  const rule = SpreadsheetApp.newDataValidation().requireValueInList(['Issued', 'Checked in', 'Cancelled'], true).build();
  sheet.getRange(2, 13, sheet.getMaxRows() - 1, 1).setDataValidation(rule);
}

function sheet_() { return SpreadsheetApp.getActive().getSheetByName(SHEET_NAME); }
function json_(obj) { return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON); }
function text_(v) { return String(v == null ? '' : v).slice(0, 2000); }

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.action === 'create') return json_(create_(body));
    if (body.action === 'lookup') return json_(lookup(body.code));
    if (body.action === 'confirm') return json_(confirmCheckin(body.code, body.pin, body.staff));
    return json_({ ok: false, error: 'Unknown action' });
  } catch (err) {
    return json_({ ok: false, error: String(err.message || err) });
  }
}

function doGet() { return json_({ ok: true, service: 'check-in passes' }); }

/** Saves a new pass from the generator. */
function create_(body) {
  if (body.key !== API_KEY) return { ok: false, error: 'Wrong API key' };
  const p = body.pass || {};
  if (!/^[A-Z0-9]{10}$/.test(p.code || '')) return { ok: false, error: 'Invalid code' };
  const lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    if (findRow_(p.code)) return { ok: false, error: 'Code already exists' };
    sheet_().appendRow([p.code, text_(p.reference), text_(p.guest), text_(p.email), text_(p.phone), Number(p.guests) || '',
      text_(p.property), text_(p.address), text_(p.checkin), text_(p.checkout), text_(p.notes), new Date(), 'Issued', '', '']);
  } finally { lock.releaseLock(); }
  return { ok: true };
}

function findRow_(code) {
  const s = sheet_(); const last = s.getLastRow(); if (last < 2) return null;
  const hit = s.getRange(2, 1, last - 1, 1).createTextFinder(code).matchEntireCell(true).findNext();
  return hit ? hit.getRow() : null;
}

function record_(row) {
  const v = sheet_().getRange(row, 1, 1, HEADERS.length).getDisplayValues()[0];
  const r = {}; HEADERS.forEach((h, i) => r[h] = v[i]); return r;
}

function blocker_(r) {
  const today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  if (r['Status'] === 'Checked in') return 'Already used: checked in on ' + r['Checked in at'] + (r['Checked in by'] ? ' by ' + r['Checked in by'] : '');
  if (r['Status'] === 'Cancelled') return 'This booking was cancelled';
  if (today < r['Check-in']) return 'Check-in opens on ' + r['Check-in'];
  if (today > r['Check-out']) return 'This stay ended on ' + r['Check-out'];
  return '';
}

function cleanCode_(input) {
  const s = String(input || '').trim();
  const m = s.match(/[?&]code=([A-Za-z0-9]+)/);
  return (m ? m[1] : s).replace(/\s+/g, '').toUpperCase();
}

/** Verify page: show the booking behind a scanned code. */
function lookup(input) {
  const code = cleanCode_(input);
  const row = /^[A-Z0-9]{10}$/.test(code) && findRow_(code);
  if (!row) return { ok: false, error: 'This code is not in the sheet. It is not a valid pass.' };
  const r = record_(row); const reason = blocker_(r);
  return { ok: true, code, record: r, valid: !reason, reason };
}

function confirmCheckin(input, pin, staffName) {
  if (String(pin) !== STAFF_PIN) return { ok: false, error: 'Wrong staff PIN' };
  const code = cleanCode_(input);
  const lock = LockService.getScriptLock(); lock.waitLock(10000);
  try {
    const row = findRow_(code);
    if (!row) return { ok: false, error: 'This code is not in the sheet.' };
    const reason = blocker_(record_(row));
    if (reason) return { ok: false, error: reason };
    const stamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm');
    sheet_().getRange(row, 13, 1, 3).setValues([['Checked in', stamp, String(staffName || '').slice(0, 60)]]);
    return { ok: true, record: record_(row) };
  } finally { lock.releaseLock(); }
}
