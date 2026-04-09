from fastapi.testclient import TestClient

from app.main import app, store


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_user_card_login_cart_order_cancel_and_pay() -> None:
    login = client.post("/api/auth/login/card", json={"uid": "04AABBCCDD"})
    assert login.status_code == 200
    token = login.json()["session_token"]

    add_item = client.post("/api/cart/items", json={"session_token": token, "item_id": 1, "quantity": 2})
    assert add_item.status_code == 200

    cart = client.get(f"/api/cart?session_token={token}")
    assert cart.status_code == 200
    assert cart.json()["total"] == "4.40"

    create_order = client.post("/api/orders/from-cart", json={"session_token": token})
    assert create_order.status_code == 200
    order_id = create_order.json()["order_id"]

    cancel = client.post(f"/api/orders/{order_id}/cancel", json={"session_token": token})
    assert cancel.status_code == 200

    # Create a second order and pay it
    client.post("/api/cart/items", json={"session_token": token, "item_id": 1, "quantity": 1})
    create_order2 = client.post("/api/orders/from-cart", json={"session_token": token})
    order_id2 = create_order2.json()["order_id"]
    pay = client.post(f"/api/orders/{order_id2}/pay", json={"session_token": token})
    assert pay.status_code == 200
    assert pay.json()["status"] == "paid"


def test_admin_login_users_search_events_and_export() -> None:
    admin_login = client.post("/api/auth/admin/login", json={"uid": "04AABBCCDD", "pincode": "1234"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["session_token"]

    users = client.get(f"/api/admin/users?session_token={admin_token}&query=sa")
    assert users.status_code == 200
    assert any("sa" in u["nickname"].lower() for u in users.json())

    create_event = client.post(
        "/api/admin/events",
        headers={"X-Session-Token": admin_token},
        json={"name": "Test Event"},
    )
    assert create_event.status_code == 200

    event_id = create_event.json()["id"]
    activate_event = client.post(f"/api/admin/events/{event_id}/activate", json={"session_token": admin_token})
    assert activate_event.status_code == 200

    export = client.get(f"/api/admin/export/{event_id}?session_token={admin_token}")
    assert export.status_code == 200
    assert export.json()["event"]["name"] == "Test Event"


def test_order_blocked_without_active_event() -> None:
    # deactivate all events
    for event in store.events.values():
        event.is_active = False

    login = client.post("/api/auth/login/card", json={"uid": "04EEFF0011"})
    token = login.json()["session_token"]
    client.post("/api/cart/items", json={"session_token": token, "item_id": 1, "quantity": 1})

    response = client.post("/api/orders/from-cart", json={"session_token": token})
    assert response.status_code == 400

    # restore active event for other tests
    store.activate_event(1)
