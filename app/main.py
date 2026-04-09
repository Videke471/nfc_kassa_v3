from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .nfc_reader import ACR122UReader, MockNFCReader
from .store import InMemoryStore

app = FastAPI(title="NFC Kassa V3")
store = InMemoryStore()
acr122u = ACR122UReader()
mock_reader = MockNFCReader()


class CardLoginRequest(BaseModel):
    uid: str


class QRLoginRequest(BaseModel):
    qr_code: str


class AdminLoginRequest(BaseModel):
    uid: str
    pincode: str


class CartItemRequest(BaseModel):
    session_token: str
    item_id: int
    quantity: int = Field(1, ge=1)


class SessionRequest(BaseModel):
    session_token: str


class CancelOrderRequest(BaseModel):
    session_token: str


class CreateUserRequest(BaseModel):
    name: str
    nickname: str
    nfc_uid: Optional[str] = None
    qr_code: Optional[str] = None
    balance: Decimal = Decimal("0.00")
    is_admin: bool = False
    is_bar_staff: bool = False
    alcohol_allowed: bool = True
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    signed_terms: bool = False


class UpdateUserRequest(BaseModel):
    nickname: Optional[str] = None
    nfc_uid: Optional[str] = None
    is_admin: Optional[bool] = None
    is_bar_staff: Optional[bool] = None
    alcohol_allowed: Optional[bool] = None
    balance: Optional[Decimal] = None


class CreateGuestRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    signed_terms: bool


class ItemRequest(BaseModel):
    name: str
    price: Decimal
    category: str
    photo_url: str = ""
    contains_alcohol: bool = False
    stock_start: int = 0
    stock_current: int = 0


class CreateEventRequest(BaseModel):
    name: str


class FeeRequest(BaseModel):
    amount: Decimal
    reason: str


class SettingRequest(BaseModel):
    printer_enabled: bool


def require_user(token: str):
    user = store.get_user_from_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Sessie ongeldig")
    return user


def require_admin(token: str):
    user = require_user(token)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin rechten vereist")
    return user


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/auth/login/card")
def login_with_card(payload: CardLoginRequest) -> dict:
    user = store.get_user_by_uid(payload.uid)
    if not user:
        raise HTTPException(status_code=404, detail="Kaart niet gevonden")
    token = store.create_session(user.id)
    return {"session_token": token, "user": {"id": user.id, "nickname": user.nickname, "balance": str(user.balance)}}


@app.post("/api/auth/login/qr")
def login_with_qr(payload: QRLoginRequest) -> dict:
    user = store.get_user_by_qr(payload.qr_code)
    if not user:
        raise HTTPException(status_code=404, detail="QR code niet gevonden of vervallen")
    token = store.create_session(user.id)
    return {"session_token": token, "user": {"id": user.id, "nickname": user.nickname, "balance": str(user.balance)}}


@app.post("/api/auth/login/scan")
def login_with_scan() -> dict:
    scan = acr122u.scan_uid() or mock_reader.scan_uid()
    if not scan:
        raise HTTPException(status_code=503, detail="Geen NFC kaart gedetecteerd")
    user = store.get_user_by_uid(scan.uid)
    if not user:
        raise HTTPException(status_code=404, detail=f"Onbekende kaart UID: {scan.uid}")
    token = store.create_session(user.id)
    return {"session_token": token, "source": scan.source, "uid": scan.uid, "user": {"id": user.id, "nickname": user.nickname}}


@app.post("/api/auth/admin/login")
def admin_login(payload: AdminLoginRequest) -> dict:
    user = store.get_user_by_uid(payload.uid)
    if not user or not user.is_admin or user.admin_pin != payload.pincode:
        raise HTTPException(status_code=401, detail="Admin login mislukt")
    token = store.create_session(user.id, role="admin")
    return {
        "session_token": token,
        "dashboard_buttons": [
            "Users",
            "Afrekenen",
            "Itembeheer",
            "Eventbeheer",
            "Stockbeheer",
            "Export",
            "Logs",
            "Instellingen",
            "Kassa sluiten",
            "Kassa afsluiten",
        ],
    }


@app.get("/api/user/me")
def user_me(session_token: str) -> dict:
    user = require_user(session_token)
    return {
        "id": user.id,
        "name": user.name,
        "nickname": user.nickname,
        "balance": str(user.balance),
        "consumed_total": str(user.consumed_total),
    }


@app.get("/api/items")
def list_items() -> list[dict]:
    items = []
    for item in store.list_menu_items():
        items.append(
            {
                "id": item.id,
                "name": item.name,
                "price": str(item.price),
                "category": item.category,
                "contains_alcohol": item.contains_alcohol,
                "stock_current": item.stock_current,
                "is_sold_out": item.stock_current <= 0,
            }
        )
    return items


@app.post("/api/cart/items")
def add_cart_item(payload: CartItemRequest) -> dict:
    user = require_user(payload.session_token)
    error = store.add_to_cart(user.id, payload.item_id, payload.quantity)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return {"cart": store.cart_for(user.id)}


@app.get("/api/cart")
def get_cart(session_token: str) -> dict:
    user = require_user(session_token)
    cart = store.cart_for(user.id)
    total = Decimal("0.00")
    lines = []
    for item_id, qty in cart.items():
        item = store.items[item_id]
        line_total = item.price * qty
        total += line_total
        lines.append({"item_id": item_id, "name": item.name, "quantity": qty, "line_total": str(line_total)})
    return {"lines": lines, "total": str(total)}


@app.delete("/api/cart/items/{item_id}")
def delete_cart_item(item_id: int, session_token: str) -> dict:
    user = require_user(session_token)
    store.remove_from_cart(user.id, item_id)
    return {"cart": store.cart_for(user.id)}


@app.delete("/api/cart/clear")
def clear_cart(payload: SessionRequest) -> dict:
    user = require_user(payload.session_token)
    store.clear_cart(user.id)
    return {"status": "cart_cleared"}


@app.post("/api/orders/from-cart")
def create_order_from_cart(payload: SessionRequest) -> dict:
    user = require_user(payload.session_token)
    if not store.get_active_event():
        raise HTTPException(status_code=400, detail="Geen actief event")
    order = store.checkout_cart(user.id)
    if not order:
        raise HTTPException(status_code=400, detail="Bestelling kon niet aangemaakt worden")
    return {"order_id": order.id, "status": order.status, "total": str(order.total)}


@app.get("/api/orders/mine")
def list_my_orders(session_token: str) -> list[dict]:
    user = require_user(session_token)
    return [
        {"id": o.id, "total": str(o.total), "status": o.status}
        for o in store.orders.values()
        if o.user_id == user.id
    ]


@app.post("/api/orders/{order_id}/cancel")
def cancel_order(order_id: int, payload: CancelOrderRequest) -> dict:
    user = require_user(payload.session_token)
    order = store.orders.get(order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    cancelled = store.cancel_order(order_id, actor_user_id=user.id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Bestelling kan niet geannuleerd worden")
    return {"order_id": order_id, "status": "cancelled"}


@app.post("/api/orders/{order_id}/pay")
def pay_order(order_id: int, payload: SessionRequest) -> dict:
    user = require_user(payload.session_token)
    order = store.orders.get(order_id)
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Bestelling niet gevonden")
    paid_order = store.pay_order(order_id)
    if not paid_order:
        raise HTTPException(status_code=400, detail="Bestelling kan niet betaald worden")
    if paid_order.status != "paid":
        raise HTTPException(status_code=400, detail="Onvoldoende saldo")
    return {"order_id": paid_order.id, "status": paid_order.status, "remaining_balance": str(user.balance)}


@app.get("/api/admin/users")
def admin_users(session_token: str, query: str = "") -> list[dict]:
    require_admin(session_token)
    return [
        {
            "id": user.id,
            "name": user.name,
            "nickname": user.nickname,
            "nfc_uid": user.nfc_uid,
            "balance": str(user.balance),
            "is_admin": user.is_admin,
            "is_bar_staff": user.is_bar_staff,
            "alcohol_allowed": user.alcohol_allowed,
        }
        for user in store.search_users(query)
    ]


@app.post("/api/admin/users")
def admin_create_user(payload: CreateUserRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    user = store.create_user(**payload.model_dump())
    return {"id": user.id, "nickname": user.nickname}


@app.patch("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, payload: UpdateUserRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    updated = store.update_user(user_id, **payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    return {"id": updated.id, "nickname": updated.nickname}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    if not store.delete_user(user_id):
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    return {"status": "deleted"}


@app.post("/api/admin/users/{user_id}/print-temporary-qr")
def admin_print_temp_qr(user_id: int, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    code = store.generate_temporary_qr(user_id)
    if not code:
        raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")
    return {"temporary_qr_code": code, "printer_sent": store.settings["printer_enabled"]}


@app.post("/api/admin/users/guest")
def admin_create_guest(payload: CreateGuestRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    user = store.create_user(
        name=f"{payload.first_name} {payload.last_name}",
        nickname=f"Guest-{payload.first_name}",
        nfc_uid=None,
        qr_code=f"GUEST-{payload.first_name[:2].upper()}-{store._next('log')}",
        balance=Decimal("0.00"),
        is_admin=False,
        is_bar_staff=False,
        alcohol_allowed=False,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        signed_terms=payload.signed_terms,
    )
    return {"id": user.id, "qr_code": user.qr_code}


@app.get("/api/admin/settlements")
def admin_settlements(session_token: str) -> list[dict]:
    require_admin(session_token)
    return store.list_unpaid_accounts()


@app.post("/api/admin/settlements/{user_id}/new-card-fee")
def admin_new_card_fee(user_id: int, payload: SessionRequest) -> dict:
    require_admin(payload.session_token)
    fee_order = store.quick_fee(user_id, Decimal("2.50"), "Nieuwe lidkaart")
    return {"fee_order_id": fee_order.id, "amount": str(fee_order.total)}


@app.post("/api/admin/settlements/{user_id}/late-fee")
def admin_late_fee(user_id: int, payload: SessionRequest) -> dict:
    require_admin(payload.session_token)
    fee_order = store.quick_fee(user_id, Decimal("5.00"), "Rekening niet betaald")
    return {"fee_order_id": fee_order.id, "amount": str(fee_order.total)}


@app.post("/api/admin/settlements/{user_id}/add-fee")
def admin_add_fee(user_id: int, payload: FeeRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    fee_order = store.quick_fee(user_id, payload.amount, payload.reason)
    return {"fee_order_id": fee_order.id, "amount": str(fee_order.total), "reason": payload.reason}


@app.get("/api/admin/items")
def admin_items(session_token: str) -> list[dict]:
    require_admin(session_token)
    return [
        {
            "id": item.id,
            "name": item.name,
            "price": str(item.price),
            "category": item.category,
            "contains_alcohol": item.contains_alcohol,
            "stock_start": item.stock_start,
            "stock_current": item.stock_current,
        }
        for item in store.list_menu_items()
    ]


@app.post("/api/admin/items")
def admin_add_item(payload: ItemRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    menu = store.get_active_menu()
    if not menu:
        raise HTTPException(status_code=400, detail="Geen actief menu")
    item = store.add_item(**payload.model_dump(), menu_id=menu.id)
    return {"id": item.id, "name": item.name}


@app.patch("/api/admin/items/{item_id}")
def admin_patch_item(item_id: int, payload: ItemRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    item = store.update_item(item_id, **payload.model_dump())
    if not item:
        raise HTTPException(status_code=404, detail="Item niet gevonden")
    return {"id": item.id, "name": item.name}


@app.delete("/api/admin/items/{item_id}")
def admin_delete_item(item_id: int, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    if not store.delete_item(item_id):
        raise HTTPException(status_code=404, detail="Item niet gevonden")
    return {"status": "deleted"}


@app.post("/api/admin/events")
def admin_create_event(payload: CreateEventRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    event = store.create_event(payload.name)
    return {"id": event.id, "name": event.name}


@app.post("/api/admin/events/{event_id}/activate")
def admin_activate_event(event_id: int, payload: SessionRequest) -> dict:
    require_admin(payload.session_token)
    event = store.activate_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event niet gevonden")
    return {"id": event.id, "name": event.name, "is_active": event.is_active}


@app.get("/api/admin/events/active")
def admin_active_event(session_token: str) -> dict:
    require_admin(session_token)
    event = store.get_active_event()
    if not event:
        raise HTTPException(status_code=404, detail="Geen actief event")
    return {"id": event.id, "name": event.name}


@app.get("/api/admin/export/{event_id}")
def admin_export(event_id: int, session_token: str) -> dict:
    require_admin(session_token)
    if event_id not in store.events:
        raise HTTPException(status_code=404, detail="Event niet gevonden")
    return store.export_event_summary(event_id)


@app.get("/api/admin/logs")
def admin_logs(session_token: str) -> list[dict]:
    require_admin(session_token)
    return store.list_logs()


@app.post("/api/admin/settings")
def admin_settings(payload: SettingRequest, session_token: str = Header(..., alias="X-Session-Token")) -> dict:
    require_admin(session_token)
    store.settings["printer_enabled"] = payload.printer_enabled
    return store.settings


@app.post("/api/admin/kassa/close")
def admin_kassa_close(payload: SessionRequest) -> dict:
    require_admin(payload.session_token)
    store.settings["cash_register_open"] = False
    return {"cash_register_open": False}


@app.post("/api/admin/kassa/open")
def admin_kassa_open(payload: AdminLoginRequest) -> dict:
    user = store.get_user_by_uid(payload.uid)
    if not user or not user.is_admin or user.admin_pin != payload.pincode:
        raise HTTPException(status_code=401, detail="Alleen admin kan kassa openen")
    store.settings["cash_register_open"] = True
    return {"cash_register_open": True}


@app.post("/api/admin/system/shutdown")
def admin_shutdown(payload: SessionRequest) -> dict:
    require_admin(payload.session_token)
    store._log("system.shutdown", "Veilige afsluitprocedure gestart")
    return {"status": "shutdown_requested", "safe": True}


static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (static_dir / "index.html").read_text(encoding="utf-8")
