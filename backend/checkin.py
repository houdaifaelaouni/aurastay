"""Check-in passes: a PDF with a signed QR code that agency staff scan once on arrival."""
import io
import os
import secrets
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlparse, parse_qs

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from auth import repo
from core import db, iso
from models import Strict

router = APIRouter()
AUDIENCE = 'aurastay:checkin'
CHECKIN_FIELDS = ['id', 'reference', 'property_id', 'property_name', 'guest_name', 'guests', 'check_in', 'check_out',
                  'status', 'rental_status', 'checkin_status', 'checked_in_at', 'checked_in_by_name']


def secret():
    # A dedicated secret keeps check-in codes separate from login sessions; the audience claim does too.
    return os.environ.get('CHECKIN_SECRET') or os.environ['JWT_SECRET']


async def ensure_nonce(booking):
    """Each booking carries one random nonce; a code is only valid while its nonce matches."""
    if booking.get('checkin_nonce'): return booking['checkin_nonce']
    nonce = secrets.token_urlsafe(12)
    await db.bookings.update_one({'id': booking['id'], 'checkin_nonce': {'$exists': False}}, {'$set': {'checkin_nonce': nonce}})
    stored = await db.bookings.find_one({'id': booking['id']}, {'_id': 0, 'checkin_nonce': 1})
    return stored['checkin_nonce']


def issue_code(booking, nonce):
    expires = datetime.combine(date.fromisoformat(booking['check_out']) + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return jwt.encode({'aud': AUDIENCE, 'bid': booking['id'], 'n': nonce, 'exp': expires}, secret(), algorithm='HS256')


def qr_payload(code):
    app_url = (os.environ.get('PUBLIC_APP_URL') or '').strip().rstrip('/')
    # With an app URL, a phone camera opens the workspace scan page directly; otherwise the raw code is scanned in-app.
    return f'{app_url}/workspace/checkin?code={code}' if app_url else code


def extract_code(value):
    value = value.strip()
    if value.startswith(('http://', 'https://')):
        value = (parse_qs(urlparse(value).query).get('code') or [''])[0]
    return value


def decode_code(value):
    try:
        return jwt.decode(extract_code(value), secret(), algorithms=['HS256'], audience=AUDIENCE)
    except jwt.ExpiredSignatureError:
        raise HTTPException(410, 'This check-in code has expired because the stay has ended')
    except jwt.PyJWTError:
        raise HTTPException(400, 'This is not a valid AuraStay check-in code')


def render_pdf(booking, property_doc, agency, code):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f'Check-in pass {booking["reference"]}')
    pdf.setAuthor('AuraStay')
    width, height = A4
    ink, muted, accent = colors.HexColor('#1f2a24'), colors.HexColor('#6b7280'), colors.HexColor('#2f5d50')

    pdf.setFillColor(accent)
    pdf.rect(0, height - 38 * mm, width, 38 * mm, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont('Helvetica-Bold', 22)
    pdf.drawString(20 * mm, height - 20 * mm, 'AuraStay')
    pdf.setFont('Helvetica', 12)
    pdf.drawString(20 * mm, height - 28 * mm, 'Check-in pass')
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawRightString(width - 20 * mm, height - 20 * mm, booking['reference'])
    pdf.setFont('Helvetica', 9)
    pdf.drawRightString(width - 20 * mm, height - 28 * mm, 'Booking reference')

    size = 70 * mm
    widget = QrCodeWidget(qr_payload(code), barLevel='M')
    x0, y0, x1, y1 = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    drawing.add(widget)
    qr_x, qr_y = width - 20 * mm - size, height - 50 * mm - size
    renderPDF.draw(drawing, pdf, qr_x, qr_y)
    pdf.setFillColor(muted)
    pdf.setFont('Helvetica', 8)
    pdf.drawCentredString(qr_x + size / 2, qr_y - 4 * mm, 'Show this code to the agency on arrival')

    check_in, check_out = date.fromisoformat(booking['check_in']), date.fromisoformat(booking['check_out'])
    nights = (check_out - check_in).days
    parts = [x.strip() for value in [property_doc.get('address'), property_doc.get('city'), property_doc.get('country')] for x in (value or '').split(',')]
    address = ', '.join(dict.fromkeys(x for x in parts if x))
    rows = [('Guest', booking['guest_name']), ('Email', booking.get('guest_email', '')), ('Phone', booking.get('guest_phone', '')),
            ('Guests', str(booking.get('guests', ''))), ('Property', booking['property_name']), ('Address', address),
            ('Check-in', check_in.strftime('%A %d %B %Y')), ('Check-out', check_out.strftime('%A %d %B %Y')),
            ('Nights', str(nights)), ('Rental balance', (booking.get('rental_status') or 'unpaid').replace('_', ' '))]
    y = height - 54 * mm
    for label, value in rows:
        pdf.setFillColor(muted)
        pdf.setFont('Helvetica', 8)
        pdf.drawString(20 * mm, y, label.upper())
        pdf.setFillColor(ink)
        pdf.setFont('Helvetica-Bold', 11)
        pdf.drawString(20 * mm, y - 5 * mm, str(value)[:58])
        y -= 13 * mm

    y -= 4 * mm
    pdf.setStrokeColor(colors.HexColor('#e5e7eb'))
    pdf.line(20 * mm, y, width - 20 * mm, y)
    y -= 9 * mm
    pdf.setFillColor(ink)
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(20 * mm, y, f'Hosted by {agency.get("name", "your agency")}')
    pdf.setFont('Helvetica', 9)
    pdf.setFillColor(muted)
    contact = ' · '.join(x for x in [agency.get('phone'), agency.get('email')] if x)
    if contact: pdf.drawString(20 * mm, y - 5 * mm, contact)
    text = pdf.beginText(20 * mm, y - 14 * mm)
    text.setFont('Helvetica', 9)
    for line in wrap(booking.get('payment_instructions') or '', 105): text.textLine(line)
    pdf.drawText(text)

    pdf.setFont('Helvetica', 7.5)
    pdf.drawString(20 * mm, 15 * mm, 'This QR code is personal and can be used once. It expires the day after check-out.')
    pdf.drawRightString(width - 20 * mm, 15 * mm, f'Issued {datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")}')
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def wrap(value, width):
    lines, line = [], ''
    for word in value.split():
        if line and len(line) + len(word) + 1 > width: lines.append(line); line = word
        else: line = f'{line} {word}'.strip()
    return lines + ([line] if line else [])


async def pass_pdf(booking):
    if booking['status'] != 'confirmed':
        raise HTTPException(400, 'A check-in pass is only available for confirmed reservations')
    nonce = await ensure_nonce(booking)
    property_doc = await db.properties.find_one({'id': booking['property_id']}, {'_id': 0, 'address': 1, 'city': 1, 'country': 1}) or {}
    agency = await db.agencies.find_one({'id': booking['agency_id']}, {'_id': 0, 'name': 1, 'email': 1, 'phone': 1}) or {}
    content = render_pdf(booking, property_doc, agency, issue_code(booking, nonce))
    return Response(content, media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="aurastay-checkin-{booking["reference"]}.pdf"', 'Cache-Control': 'no-store'})


@router.get('/workspace/bookings/{id}/checkin-pass')
async def workspace_pass(id: str, r=Depends(repo)):
    return await pass_pdf(await r.get('bookings', id))


@router.get('/bookings/status/{token}/checkin-pass')
async def guest_pass(token: str):
    if len(token) < 32: raise HTTPException(404, 'Reservation not found')
    booking = await db.bookings.find_one({'status_token': token}, {'_id': 0})
    if not booking: raise HTTPException(404, 'Reservation not found')
    return await pass_pdf(booking)


class CheckinCode(Strict):
    code: str = Field(min_length=10, max_length=2000)


async def scanned_booking(code, r):
    claims = decode_code(code)
    booking = await r.get('bookings', claims['bid'])  # 404 for another agency's booking
    if not booking.get('checkin_nonce') or not secrets.compare_digest(booking['checkin_nonce'], claims['n']):
        raise HTTPException(400, 'This check-in code has been replaced and is no longer valid')
    return booking


def blocker(booking):
    if booking.get('checkin_status') == 'checked_in':
        return f'Already used: this guest checked in on {booking["checked_in_at"][:16].replace("T", " ")} UTC'
    if booking['status'] != 'confirmed':
        return f'This reservation is {booking["status"].replace("_", " ")} and cannot be checked in'
    if date.today().isoformat() < booking['check_in']:
        return f'Check-in opens on {booking["check_in"]}'
    if date.today().isoformat() > booking['check_out']:
        return 'This stay has already ended'
    return None


def summary(booking):
    reason = blocker(booking)
    return {**{k: booking.get(k) for k in CHECKIN_FIELDS}, 'valid': reason is None, 'reason': reason}


@router.post('/workspace/checkin/verify')
async def verify(data: CheckinCode, r=Depends(repo)):
    return summary(await scanned_booking(data.code, r))


@router.post('/workspace/checkin/confirm')
async def confirm(data: CheckinCode, r=Depends(repo)):
    booking = await scanned_booking(data.code, r)
    reason = blocker(booking)
    if reason: raise HTTPException(409, reason)
    # Conditional update: two staff scanning the same code at once cannot both succeed.
    query = r.query({'id': booking['id'], 'status': 'confirmed', 'checkin_status': {'$ne': 'checked_in'}}, write=True)
    result = await db.bookings.update_one(query, {'$set': {'checkin_status': 'checked_in', 'checked_in_at': iso(),
                                                           'checked_in_by': r.p['id'], 'checked_in_by_name': r.p.get('name', '')}})
    if not result.modified_count:
        raise HTTPException(409, blocker(await r.get('bookings', booking['id'])) or 'This code has already been used')
    return summary(await r.get('bookings', booking['id']))
