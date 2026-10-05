"""Check-in pass tests. Runs in-process against mongomock, so no live server or MongoDB is needed."""
import io
import os
from datetime import date, timedelta

import jwt
import pytest

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('DB_NAME', 'aurastay_test')
os.environ.setdefault('JWT_SECRET', 'test-secret-key-that-is-at-least-32-bytes')

mongomock_motor = pytest.importorskip('mongomock_motor')
pypdf = pytest.importorskip('pypdf')
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import checkin
import core


@pytest.fixture
def client(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()['aurastay_test']
    for module in (core, auth, checkin):
        monkeypatch.setattr(module, 'db', db)
    app = FastAPI()
    app.include_router(auth.router, prefix='/api')
    app.include_router(checkin.router, prefix='/api')
    today = date.today()

    async def seed():
        await db.agencies.insert_many([{'id': 'a1', 'name': 'Costa Living', 'active': True, 'phone': '+34 1', 'email': 'a@x.com'},
                                       {'id': 'a2', 'name': 'Maison', 'active': True}])
        for uid, agency in [('u1', 'a1'), ('u2', 'a2')]:
            await db.users.insert_one({'id': uid, 'name': f'Staff {uid}', 'email': f'{uid}@x.com', 'active': True})
            await db.memberships.insert_one({'id': f'm{uid}', 'user_id': uid, 'agency_id': agency, 'tenant_role': 'admin', 'active': True})
        await db.properties.insert_one({'id': 'p1', 'agency_id': 'a1', 'address': 'Calle 1', 'city': 'Marbella', 'country': 'Spain'})
        base = {'agency_id': 'a1', 'property_id': 'p1', 'property_name': 'Casa Sol', 'guest_name': 'Emma Wilson',
                'guest_email': 'emma@example.com', 'guest_phone': '+44 7700', 'guests': 2, 'status': 'confirmed',
                'rental_status': 'unpaid', 'payment_instructions': 'Pay the agency before arrival.'}
        await db.bookings.insert_many([
            {**base, 'id': 'today', 'reference': 'AUR-1', 'status_token': 't' * 40,
             'check_in': today.isoformat(), 'check_out': (today + timedelta(days=3)).isoformat()},
            {**base, 'id': 'future', 'reference': 'AUR-2', 'check_in': (today + timedelta(days=5)).isoformat(),
             'check_out': (today + timedelta(days=8)).isoformat()},
            {**base, 'id': 'cancelled', 'reference': 'AUR-3', 'status': 'cancelled', 'check_in': today.isoformat(),
             'check_out': (today + timedelta(days=2)).isoformat()},
        ])

    with TestClient(app) as c:
        c.portal.call(seed)
        c.db = db
        yield c


def headers(user='u1'):
    token = jwt.encode({'sub': user, 'exp': 9999999999}, os.environ['JWT_SECRET'], algorithm='HS256')
    return {'Authorization': f'Bearer {token}'}


def code_from_pdf(content):
    # The QR payload is not text in the PDF, so re-derive the code the same way the endpoint does.
    assert content.startswith(b'%PDF')
    text = pypdf.PdfReader(io.BytesIO(content)).pages[0].extract_text()
    assert 'AUR-1' in text and 'Emma Wilson' in text and 'Casa Sol' in text
    return text


def issued_code(client, booking_id):
    booking = client.portal.call(client.db.bookings.find_one, {'id': booking_id})
    return checkin.issue_code(booking, booking['checkin_nonce'])


def test_workspace_and_guest_pdf(client):
    r = client.get('/api/workspace/bookings/today/checkin-pass', headers=headers())
    assert r.status_code == 200 and r.headers['content-type'] == 'application/pdf'
    code_from_pdf(r.content)
    nonce = client.portal.call(client.db.bookings.find_one, {'id': 'today'})['checkin_nonce']
    r = client.get('/api/bookings/status/' + 't' * 40 + '/checkin-pass')
    assert r.status_code == 200
    assert client.portal.call(client.db.bookings.find_one, {'id': 'today'})['checkin_nonce'] == nonce


def test_pdf_scoped_and_confirmed_only(client):
    assert client.get('/api/workspace/bookings/today/checkin-pass', headers=headers('u2')).status_code == 404
    assert client.get('/api/workspace/bookings/cancelled/checkin-pass', headers=headers()).status_code == 400
    assert client.get('/api/workspace/bookings/today/checkin-pass').status_code == 401


def test_scan_once(client):
    client.get('/api/workspace/bookings/today/checkin-pass', headers=headers())
    code = issued_code(client, 'today')
    r = client.post('/api/workspace/checkin/verify', json={'code': code}, headers=headers())
    assert r.status_code == 200 and r.json()['valid'] and r.json()['guest_name'] == 'Emma Wilson'
    r = client.post('/api/workspace/checkin/confirm', json={'code': code}, headers=headers())
    assert r.status_code == 200 and r.json()['checkin_status'] == 'checked_in'
    r = client.post('/api/workspace/checkin/confirm', json={'code': code}, headers=headers())
    assert r.status_code == 409 and 'Already used' in r.json()['detail']
    r = client.post('/api/workspace/checkin/verify', json={'code': code}, headers=headers())
    assert r.json()['valid'] is False and 'Already used' in r.json()['reason']


def test_scanned_url_is_accepted(client, monkeypatch):
    client.get('/api/workspace/bookings/today/checkin-pass', headers=headers())
    monkeypatch.setenv('PUBLIC_APP_URL', 'https://aurastay.example')
    url = checkin.qr_payload(issued_code(client, 'today'))
    assert url.startswith('https://aurastay.example/workspace/checkin?code=')
    assert client.post('/api/workspace/checkin/verify', json={'code': url}, headers=headers()).json()['valid']


def test_rejects_tampered_foreign_and_early_codes(client):
    client.get('/api/workspace/bookings/today/checkin-pass', headers=headers())
    code = issued_code(client, 'today')
    tampered = code[:-3] + ('aaa' if not code.endswith('aaa') else 'bbb')
    assert client.post('/api/workspace/checkin/verify', json={'code': tampered}, headers=headers()).status_code == 400
    forged = jwt.encode({'aud': checkin.AUDIENCE, 'bid': 'today', 'n': 'x', 'exp': 9999999999}, 'wrong', algorithm='HS256')
    assert client.post('/api/workspace/checkin/verify', json={'code': forged}, headers=headers()).status_code == 400
    login_token = headers()['Authorization'][7:]
    assert client.post('/api/workspace/checkin/verify', json={'code': login_token}, headers=headers()).status_code == 400
    assert client.post('/api/workspace/checkin/confirm', json={'code': code}, headers=headers('u2')).status_code == 404
    client.get('/api/workspace/bookings/future/checkin-pass', headers=headers())
    r = client.post('/api/workspace/checkin/confirm', json={'code': issued_code(client, 'future')}, headers=headers())
    assert r.status_code == 409 and 'opens on' in r.json()['detail']


def test_replaced_nonce_invalidates_code(client):
    client.get('/api/workspace/bookings/today/checkin-pass', headers=headers())
    code = issued_code(client, 'today')
    client.portal.call(client.db.bookings.update_one, {'id': 'today'}, {'$set': {'checkin_nonce': 'rotated'}})
    r = client.post('/api/workspace/checkin/verify', json={'code': code}, headers=headers())
    assert r.status_code == 400 and 'replaced' in r.json()['detail']
