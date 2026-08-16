import importlib
import sys
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def clients(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'expense-splitter-test.db'}")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("TRUSTED_HOSTS", "testserver,localhost")
    monkeypatch.setenv("RECEIPT_DIR", str(tmp_path / "receipts"))
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)
    main = importlib.import_module("app.main")
    with TestClient(main.app) as owner, TestClient(main.app) as member, TestClient(main.app) as outsider:
        yield owner, member, outsider
    main.engine.dispose()


def register(client, username, email, name):
    response = client.post("/api/auth/register", json={"username": username, "email": email, "name": name, "password": "correct-horse-battery"})
    assert response.status_code == 201, response.text
    return response.json()


def test_group_roles_requests_and_lifecycle_are_scoped(clients):
    owner, member, outsider = clients
    register(owner, "owner", "owner@example.com", "Owner")
    group_response = owner.post("/api/groups", json={"name": "Dinner"})
    assert group_response.status_code == 201
    group = group_response.json()

    register(member, "member", "member@example.com", "Member")
    invite = owner.post(f"/api/groups/{group['id']}/invites")
    assert invite.status_code == 201
    assert member.post(f"/api/invites/{invite.json()['token']}/accept").status_code == 200

    guest = owner.post(f"/api/groups/{group['id']}/people", json={"name": "Guest"})
    assert guest.status_code == 201
    assert member.post(f"/api/groups/{group['id']}/people", json={"name": "Tamper"}).status_code == 403

    expense = owner.post(f"/api/groups/{group['id']}/expenses", json={
        "title": "Dinner",
        "bills": [{"category": "飲食", "description": "Noodles", "amount": "100.00", "participant_ids": [group["participants"][0]["id"], guest.json()["id"]], "split_method": "EQUAL", "allocations": {}}],
    })
    assert expense.status_code == 201, expense.text
    event = expense.json()
    assert Decimal(event["bills"][0]["shares"][guest.json()["id"]]) == Decimal("50.00")
    assert member.get(f"/api/expenses/{event['id']}").status_code == 200

    billing_request = owner.post(f"/api/groups/{group['id']}/billing-requests", json={"participant_id": guest.json()["id"], "amount": "50.00", "note": "晚飯", "event_id": event["id"]})
    assert billing_request.status_code == 201, billing_request.text
    request_id = billing_request.json()["id"]
    share_update = owner.patch(f"/api/bills/{event['bills'][0]['id']}/shares/{guest.json()['id']}?confirmed=true")
    assert share_update.status_code == 200
    assert guest.json()["id"] in share_update.json()["confirmed_participant_ids"]
    assert owner.patch(f"/api/bills/{event['bills'][0]['id']}/shares/{guest.json()['id']}?confirmed=false").status_code == 200
    assert owner.delete(f"/api/groups/{group['id']}/participants/{guest.json()['id']}").status_code == 409
    assert owner.patch(f"/api/groups/{group['id']}/billing-requests/{request_id}", json={"status": "COMPLETED"}).status_code == 200
    assert owner.patch(f"/api/groups/{group['id']}/billing-requests/{request_id}", json={"status": "CANCELLED"}).status_code == 409

    register(outsider, "outsider", "outsider@example.com", "Outsider")
    assert outsider.get(f"/api/groups/{group['id']}/expenses").status_code == 403
    other_group = owner.post("/api/groups", json={"name": "Other"}).json()
    tampered_expense = owner.post(f"/api/groups/{other_group['id']}/expenses", json={
        "title": "Tamper", "bills": [{"category": "飲食", "description": "Bad", "amount": "10.00", "participant_ids": [guest.json()["id"]], "split_method": "EQUAL", "allocations": {}}],
    })
    assert tampered_expense.status_code == 400

    assert owner.post(f"/api/groups/{group['id']}/leave").status_code == 409
    assert member.post(f"/api/groups/{group['id']}/leave").status_code == 204
    assert member.delete("/api/account").status_code == 204


def test_receipt_rejects_mismatched_file_content(clients):
    owner, _, _ = clients
    register(owner, "receipt-owner", "receipt-owner@example.com", "Receipt Owner")
    group = owner.post("/api/groups", json={"name": "Receipts"}).json()
    event = owner.post(f"/api/groups/{group['id']}/expenses", json={
        "title": "Receipt", "bills": [{"category": "飲食", "description": "Lunch", "amount": "10.00", "participant_ids": [group["participants"][0]["id"]], "split_method": "EQUAL", "allocations": {}}],
    }).json()
    bill_id = event["bills"][0]["id"]
    response = owner.post(f"/api/bills/{bill_id}/receipt", files={"file": ("fake.png", b"not-a-png", "image/png")})
    assert response.status_code == 400
