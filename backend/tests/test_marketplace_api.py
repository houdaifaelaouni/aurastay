import os
from datetime import date, timedelta
from io import BytesIO

import pytest
import requests
from dotenv import load_dotenv


load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
OWNER_EMAIL = os.environ.get("BOOTSTRAP_EMAIL")
OWNER_PASSWORD = os.environ.get("BOOTSTRAP_PASSWORD")
MANAGER_EMAIL = os.environ.get("MANAGER_EMAIL")
MANAGER_PASSWORD = os.environ.get("MANAGER_PASSWORD")
CRON_SECRET = os.environ.get("WEBHOOK_CRON_SECRET")


def api(path: str) -> str:
    return f"{BASE_URL}/api{path}"


@pytest.fixture(scope="session")
def session_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def owner_token(session_client):
    if not OWNER_EMAIL or not OWNER_PASSWORD:
        pytest.skip("Owner credentials missing")
    r = session_client.post(api("/auth/login"), json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    assert isinstance(token, str) and token
    return token


@pytest.fixture(scope="session")
def manager_token(session_client):
    if not MANAGER_EMAIL or not MANAGER_PASSWORD:
        pytest.skip("Manager credentials missing")
    r = session_client.post(api("/auth/login"), json={"email": MANAGER_EMAIL, "password": MANAGER_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    token = r.json().get("token")
    assert isinstance(token, str) and token
    return token


@pytest.fixture(scope="session")
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture(scope="session")
def manager_headers(manager_token):
    return {"Authorization": f"Bearer {manager_token}"}


# Public catalogue + detail + quote + checkout flows
def test_catalogue_has_seeded_properties(session_client):
    r = session_client.get(api("/properties"), timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 8
    assert len(data["properties"]) == 8
    assert all(p["status"] if "status" in p else True for p in data["properties"])


def test_catalogue_filtering_and_sorting(session_client):
    params = {
        "destination": "Spain",
        "category": "City breaks",
        "sort": "price_desc",
        "max_price": 200,
        "amenities": "Wi-Fi,Kitchen",
        "guests": 2,
    }
    r = session_client.get(api("/properties"), params=params, timeout=20)
    assert r.status_code == 200, r.text
    rows = r.json()["properties"]
    assert len(rows) > 0
    prices = [p["price"] for p in rows]
    assert prices == sorted(prices, reverse=True)
    assert all(p["price"] <= 200 for p in rows)
    assert all("Wi-Fi" in p["amenities"] and "Kitchen" in p["amenities"] for p in rows)


def test_catalogue_rejects_invalid_date_ranges(session_client):
    today = date.today()
    params = {"check_in": today.isoformat(), "check_out": today.isoformat()}
    r = session_client.get(api("/properties"), params=params, timeout=20)
    assert r.status_code == 400
    assert "valid future dates" in r.json()["detail"]


def test_property_detail_omits_private_fields(session_client):
    r = session_client.get(api("/properties/stay-1"), timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["id"] == "stay-1"
    assert data["payments_enabled"] is False
    assert "commission_rate" not in data
    assert "agency_rate" not in data


def test_quote_clamp_formula_and_service_math(session_client):
    check_in = date.today() + timedelta(days=40)
    check_out = check_in + timedelta(days=5)
    payload = {
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "guests": 2,
        "services": ["transfer"],
    }
    r = session_client.post(api("/properties/stay-1/quote"), json=payload, timeout=20)
    assert r.status_code == 200, r.text
    q = r.json()
    assert q["nights"] == 5
    assert q["accommodation"] == 1225.0
    assert q["reservation_fee"] == 17.25
    assert q["services_total"] == 45.0
    assert q["rental_balance"] == 1270.0
    assert q["total"] == 1287.25
    assert q["currency"] == "EUR"
    assert q["payments_enabled"] is False


def test_quote_rejects_unavailable_dates(session_client):
    availability = session_client.get(api("/properties/stay-1/availability"), timeout=20)
    assert availability.status_code == 200, availability.text
    slots = availability.json()
    assert len(slots) > 0
    blocked = slots[0]
    payload = {
        "check_in": blocked["check_in"],
        "check_out": blocked["check_out"],
        "guests": 2,
        "services": [],
    }
    q = session_client.post(api("/properties/stay-1/quote"), json=payload, timeout=20)
    assert q.status_code == 409
    assert "unavailable" in q.json()["detail"].lower()


def test_checkout_is_intentionally_disabled(session_client):
    check_in = date.today() + timedelta(days=50)
    check_out = check_in + timedelta(days=3)
    payload = {
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "guests": 2,
        "services": [],
        "guest_name": "TEST Guest",
        "guest_email": "test.guest@example.com",
        "guest_phone": "+3531234567",
        "accepted_terms": True,
    }
    r = session_client.post(api("/properties/stay-1/checkout"), json=payload, timeout=20)
    assert r.status_code == 503
    assert "No payment has been taken" in r.json()["detail"]


# Auth + tenant authorization matrix
def test_anonymous_workspace_access_denied(session_client):
    r = session_client.get(api("/workspace/properties"), timeout=20)
    assert r.status_code == 401
    assert "sign in" in r.json()["detail"].lower()


def test_manager_cannot_access_platform_routes(session_client, manager_headers):
    r = session_client.get(api("/platform/settings"), headers=manager_headers, timeout=20)
    assert r.status_code == 403
    assert "permission" in r.json()["detail"].lower()


def test_manager_foreign_agency_header_is_denied(session_client, manager_headers):
    headers = {**manager_headers, "X-Agency-Id": "agency-maison"}
    r = session_client.get(api("/workspace/properties"), headers=headers, timeout=20)
    assert r.status_code == 404
    assert "workspace not found" in r.json()["detail"].lower()


def test_owner_read_all_agencies_and_write_requires_scope(session_client, owner_headers):
    # owner can read all agencies without selecting one
    r = session_client.get(api("/agencies"), headers=owner_headers, timeout=20)
    assert r.status_code == 200, r.text
    agencies = r.json()
    assert any(a["id"] == "agency-costa" for a in agencies)
    assert any(a["id"] == "agency-maison" for a in agencies)

    # owner write without agency selection must fail
    payload = {
        "name": "TEST Owner Scope Property",
        "city": "Madrid",
        "country": "Spain",
        "address": "Test address",
        "type": "Apartment",
        "category": "City breaks",
        "description": "This is a valid property description with enough characters.",
        "price": 111,
        "commission_rate": 15,
        "guests": 2,
        "bedrooms": 1,
        "bathrooms": 1,
        "amenities": ["Wi-Fi", "Kitchen"],
        "photos": ["https://example.com/image.jpg"],
        "services": [],
        "status": "draft",
    }
    w = session_client.post(api("/workspace/properties"), headers=owner_headers, json=payload, timeout=20)
    assert w.status_code == 400
    assert "select an agency" in w.json()["detail"].lower()


def test_forbidden_extra_fields_rejected(session_client, manager_headers):
    payload = {
        "check_in": (date.today() + timedelta(days=60)).isoformat(),
        "check_out": (date.today() + timedelta(days=62)).isoformat(),
        "guests": 2,
        "services": [],
        "hacker": "x",
    }
    r = session_client.post(api("/properties/stay-1/quote"), json=payload, timeout=20)
    assert r.status_code == 422
    assert any("extra" in x["msg"].lower() for x in r.json()["detail"])


# Calendar blocks and overlap protection
def test_block_overlap_rejected_and_cleanup(session_client, manager_headers):
    start = date.today() + timedelta(days=120)
    end = start + timedelta(days=4)
    payload = {
        "check_in": start.isoformat(),
        "check_out": end.isoformat(),
        "reason": "TEST maintenance block",
        "kind": "maintenance",
    }
    create = session_client.post(api("/workspace/properties/stay-1/blocks"), headers=manager_headers, json=payload, timeout=20)
    assert create.status_code == 200, create.text
    bid = create.json()["id"]

    overlap_payload = {
        "check_in": (start + timedelta(days=1)).isoformat(),
        "check_out": (end + timedelta(days=1)).isoformat(),
        "reason": "TEST overlap",
        "kind": "owner",
    }
    overlap_resp = session_client.post(api("/workspace/properties/stay-1/blocks"), headers=manager_headers, json=overlap_payload, timeout=20)
    assert overlap_resp.status_code == 409

    delete = session_client.delete(api(f"/workspace/blocks/{bid}"), headers=manager_headers, timeout=20)
    assert delete.status_code == 200
    assert delete.json()["ok"] is True


# Cron endpoint auth/body/idempotency
def test_cron_requires_auth_and_valid_payload(session_client):
    invalid_auth = session_client.post(api("/cron/expire-holds"), json={}, timeout=20)
    assert invalid_auth.status_code == 401

    if not CRON_SECRET:
        pytest.skip("WEBHOOK_CRON_SECRET missing")

    headers = {"Authorization": f"Bearer {CRON_SECRET}", "Content-Type": "application/json"}
    bad_body = session_client.post(api("/cron/expire-holds"), headers=headers, json={"event": "wrong"}, timeout=20)
    assert bad_body.status_code == 400
    assert "invalid" in bad_body.json()["detail"].lower()


def test_cron_accepts_and_is_idempotent(session_client):
    if not CRON_SECRET:
        pytest.skip("WEBHOOK_CRON_SECRET missing")

    run_id = f"pytest-run-{date.today().isoformat()}"
    headers = {
        "Authorization": f"Bearer {CRON_SECRET}",
        "X-Webhook-Id": run_id,
        "Content-Type": "application/json",
    }
    body = {"event": "schedule.triggered", "run_id": run_id}

    first = session_client.post(api("/cron/expire-holds"), headers=headers, json=body, timeout=20)
    assert first.status_code == 200, first.text
    assert first.json().get("accepted") is True

    second = session_client.post(api("/cron/expire-holds"), headers=headers, json=body, timeout=20)
    assert second.status_code == 200, second.text
    assert second.json().get("duplicate") is True


# Platform toggles + storage upload access and content validation
def test_disabling_agency_hides_its_public_listings(session_client, owner_headers):
    toggle_payload = {
        "name": "Maison Collective",
        "email": "stays@maisoncollective.example",
        "phone": "+33 4 00 00 12 34",
        "payment_instructions": "Please contact Maison Collective before arrival to arrange the separate accommodation and service payment.",
        "active": False,
    }
    restore_payload = {**toggle_payload, "active": True}

    try:
        disable = session_client.put(api("/platform/agencies/agency-maison"), headers=owner_headers, json=toggle_payload, timeout=20)
        assert disable.status_code == 200, disable.text
        public = session_client.get(api("/properties"), timeout=20)
        assert public.status_code == 200
        ids = [p["id"] for p in public.json()["properties"]]
        assert all(i not in ids for i in ["stay-6", "stay-7", "stay-8"])
    finally:
        session_client.put(api("/platform/agencies/agency-maison"), headers=owner_headers, json=restore_payload, timeout=20)


def test_disabled_manager_token_denied_until_reenabled(session_client, owner_headers, manager_token):
    headers = {"Authorization": f"Bearer {manager_token}"}
    try:
        off = session_client.patch(api("/platform/managers/manager"), headers=owner_headers, json={"active": False}, timeout=20)
        assert off.status_code == 200, off.text

        denied = session_client.get(api("/auth/me"), headers=headers, timeout=20)
        assert denied.status_code == 401
        assert "session expired" in denied.json()["detail"].lower()
    finally:
        session_client.patch(api("/platform/managers/manager"), headers=owner_headers, json={"active": True}, timeout=20)


def test_upload_rejects_unsupported_content_type(session_client, manager_headers):
    auth_only = {"Authorization": manager_headers["Authorization"]}
    files = {"file": ("bad.txt", BytesIO(b"not-an-image"), "text/plain")}
    r = requests.post(api("/workspace/photos"), headers=auth_only, files=files, timeout=20)
    assert r.status_code == 400
    assert "jpeg" in r.json()["detail"].lower()


def test_uploaded_draft_photo_private_then_agency_accessible(session_client, manager_headers):
    auth_only = {"Authorization": manager_headers["Authorization"]}
    png = b"\x89PNG\r\n\x1a\n" + b"PNGDATA"
    files = {"file": ("tiny.png", BytesIO(png), "image/png")}
    upload = requests.post(api("/workspace/photos"), headers=auth_only, files=files, timeout=30)
    assert upload.status_code == 200, upload.text
    media_url = upload.json()["url"]

    anon = session_client.get(f"{BASE_URL}{media_url}", timeout=20)
    assert anon.status_code == 404

    scoped = session_client.get(f"{BASE_URL}{media_url}", headers=manager_headers, timeout=20)
    assert scoped.status_code == 200
    assert scoped.headers["content-type"].startswith("image/png")


def test_workspace_csv_exports_return_csv(session_client, manager_headers):
    commissions = session_client.get(api("/workspace/commissions/export"), headers=manager_headers, timeout=20)
    assert commissions.status_code == 200, commissions.text
    assert "text/csv" in commissions.headers.get("content-type", "")
    assert "reference" in commissions.text

    expenses = session_client.get(api("/workspace/expenses/export"), headers=manager_headers, timeout=20)
    assert expenses.status_code == 200, expenses.text
    assert "text/csv" in expenses.headers.get("content-type", "")
    assert "amount_eur" in expenses.text
