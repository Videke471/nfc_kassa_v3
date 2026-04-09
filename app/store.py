from __future__ import annotations

import secrets
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from .models import Event, Item, LogEntry, Menu, Order, OrderLine, User


class InMemoryStore:
    def __init__(self) -> None:
        self.users: Dict[int, User] = {
            1: User(
                id=1,
                name="Sanne Vermeulen",
                nickname="Sanne",
                nfc_uid="04AABBCCDD",
                qr_code="QR-SANNE-001",
                balance=Decimal("50.00"),
                is_admin=True,
                admin_pin="1234",
            ),
            2: User(
                id=2,
                name="Youssef El Amrani",
                nickname="Youssef",
                nfc_uid="04EEFF0011",
                qr_code="QR-YOUSSEF-001",
                balance=Decimal("20.00"),
                is_bar_staff=True,
            ),
            3: User(
                id=3,
                name="Nora Janssens",
                nickname="Nora",
                nfc_uid="041234ABCD",
                qr_code="QR-NORA-001",
                balance=Decimal("8.75"),
                alcohol_allowed=False,
            ),
        }

        self.events: Dict[int, Event] = {
            1: Event(id=1, name="Algemene Ledenvergadering 2026", is_active=True)
        }
        self.menus: Dict[int, Menu] = {
            1: Menu(id=1, name="Standaard bar", location="Hoofdzaal", event_id=1, is_active=True)
        }

        self.items: Dict[int, Item] = {
            1: Item(id=1, name="Cola", price=Decimal("2.20"), category="Fris", photo_url="", stock_start=100, stock_current=87, menu_id=1),
            2: Item(id=2, name="Bier", price=Decimal("3.20"), category="Alcohol", photo_url="", contains_alcohol=True, stock_start=60, stock_current=42, menu_id=1),
            3: Item(id=3, name="Broodje Kaas", price=Decimal("3.95"), category="Food", photo_url="", stock_start=40, stock_current=13, menu_id=1),
        }

        self.sessions: Dict[str, int] = {}
        self.session_roles: Dict[str, str] = {}
        self.temporary_qr_codes: Dict[str, tuple[int, datetime]] = {}
        self.carts: Dict[int, Dict[int, int]] = defaultdict(dict)
        self.orders: Dict[int, Order] = {}
        self.logs: Dict[int, LogEntry] = {}
        self.settings = {"printer_enabled": True, "cash_register_open": True}

        self._next_ids = {
            "user": 4,
            "event": 2,
            "menu": 2,
            "item": 4,
            "order": 1,
            "log": 1,
        }

    def _next(self, key: str) -> int:
        current = self._next_ids[key]
        self._next_ids[key] += 1
        return current

    def _log(self, action: str, details: str, actor_user_id: Optional[int] = None) -> None:
        active_event = self.get_active_event()
        log_id = self._next("log")
        self.logs[log_id] = LogEntry(
            id=log_id,
            event_id=active_event.id if active_event else None,
            actor_user_id=actor_user_id,
            action=action,
            details=details,
        )

    def get_active_event(self) -> Optional[Event]:
        for event in self.events.values():
            if event.is_active:
                return event
        return None

    def get_active_menu(self) -> Optional[Menu]:
        for menu in self.menus.values():
            if menu.is_active:
                return menu
        return None

    def create_session(self, user_id: int, role: str = "user") -> str:
        token = secrets.token_urlsafe(24)
        self.sessions[token] = user_id
        self.session_roles[token] = role
        return token

    def get_user_from_session(self, token: str) -> Optional[User]:
        user_id = self.sessions.get(token)
        return self.users.get(user_id) if user_id else None

    def get_user_by_uid(self, uid: str) -> Optional[User]:
        needle = uid.strip().upper()
        return next((u for u in self.users.values() if (u.nfc_uid or "").upper() == needle), None)

    def get_user_by_qr(self, code: str) -> Optional[User]:
        needle = code.strip().upper()
        user = next((u for u in self.users.values() if (u.qr_code or "").upper() == needle), None)
        if user:
            return user
        temp = self.temporary_qr_codes.get(needle)
        if not temp:
            return None
        user_id, expires_at = temp
        if datetime.now(timezone.utc) > expires_at:
            return None
        return self.users.get(user_id)

    def search_users(self, query: str = "") -> List[User]:
        normalized = query.lower().strip()
        users = sorted(self.users.values(), key=lambda u: u.nickname.lower())
        if not normalized:
            return users
        return [u for u in users if normalized in u.name.lower() or normalized in u.nickname.lower()]

    def create_user(self, **kwargs: object) -> User:
        user_id = self._next("user")
        user = User(id=user_id, **kwargs)
        self.users[user_id] = user
        self._log("user.created", f"User {user.nickname} aangemaakt")
        return user

    def update_user(self, user_id: int, **kwargs: object) -> Optional[User]:
        user = self.users.get(user_id)
        if not user:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        self._log("user.updated", f"User {user.nickname} aangepast")
        return user

    def delete_user(self, user_id: int) -> bool:
        user = self.users.pop(user_id, None)
        if not user:
            return False
        self._log("user.deleted", f"User {user.nickname} verwijderd")
        return True

    def generate_temporary_qr(self, user_id: int, minutes_valid: int = 15) -> Optional[str]:
        if user_id not in self.users:
            return None
        code = f"TMP-{secrets.token_hex(4).upper()}"
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes_valid)
        self.temporary_qr_codes[code] = (user_id, expires_at)
        self._log("user.temp_qr", f"Temporary QR uitgegeven voor user_id={user_id}")
        return code

    def list_menu_items(self) -> List[Item]:
        menu = self.get_active_menu()
        if not menu:
            return []
        return [item for item in self.items.values() if item.menu_id == menu.id]

    def add_item(self, **kwargs: object) -> Item:
        item_id = self._next("item")
        item = Item(id=item_id, **kwargs)
        self.items[item_id] = item
        self._log("item.created", f"Item {item.name} toegevoegd")
        return item

    def update_item(self, item_id: int, **kwargs: object) -> Optional[Item]:
        item = self.items.get(item_id)
        if not item:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(item, key):
                setattr(item, key, value)
        self._log("item.updated", f"Item {item.name} aangepast")
        return item

    def delete_item(self, item_id: int) -> bool:
        item = self.items.pop(item_id, None)
        if not item:
            return False
        self._log("item.deleted", f"Item {item.name} verwijderd")
        return True

    def cart_for(self, user_id: int) -> Dict[int, int]:
        return self.carts[user_id]

    def clear_cart(self, user_id: int) -> None:
        self.carts[user_id] = {}

    def add_to_cart(self, user_id: int, item_id: int, quantity: int = 1) -> Optional[str]:
        item = self.items.get(item_id)
        if not item:
            return "Item bestaat niet"
        if item.stock_current <= 0:
            return "Item is uitverkocht"
        if item.contains_alcohol and not self.users[user_id].alcohol_allowed:
            return "Alcohol is niet toegestaan voor deze gebruiker"
        current_qty = self.carts[user_id].get(item_id, 0)
        if current_qty + quantity > item.stock_current:
            return "Onvoldoende stock"
        self.carts[user_id][item_id] = current_qty + quantity
        return None

    def remove_from_cart(self, user_id: int, item_id: int) -> None:
        self.carts[user_id].pop(item_id, None)

    def checkout_cart(self, user_id: int) -> Optional[Order]:
        event = self.get_active_event()
        if not event or not self.settings["cash_register_open"]:
            return None

        cart = self.carts[user_id]
        if not cart:
            return None

        lines: List[OrderLine] = []
        total = Decimal("0.00")
        for item_id, qty in cart.items():
            item = self.items[item_id]
            if item.stock_current < qty:
                return None
            line = OrderLine(item_id=item_id, quantity=qty, unit_price=item.price)
            lines.append(line)
            total += item.price * qty

        order_id = self._next("order")
        order = Order(id=order_id, user_id=user_id, event_id=event.id, lines=lines, total=total)
        self.orders[order_id] = order
        for line in lines:
            self.items[line.item_id].stock_current -= line.quantity
        self.clear_cart(user_id)
        self._log("order.created", f"Order {order_id} gemaakt door user_id={user_id}", actor_user_id=user_id)
        return order

    def cancel_order(self, order_id: int, actor_user_id: int) -> Optional[Order]:
        order = self.orders.get(order_id)
        if not order or order.status != "open":
            return None
        order.status = "cancelled"
        for line in order.lines:
            self.items[line.item_id].stock_current += line.quantity
        self._log("order.cancelled", f"Order {order_id} geannuleerd", actor_user_id=actor_user_id)
        return order

    def pay_order(self, order_id: int) -> Optional[Order]:
        order = self.orders.get(order_id)
        if not order or order.status != "open":
            return None
        user = self.users[order.user_id]
        if user.balance < order.total:
            return order
        user.balance -= order.total
        user.consumed_total += order.total
        order.status = "paid"
        self._log("order.paid", f"Order {order_id} betaald", actor_user_id=order.user_id)
        return order

    def list_unpaid_accounts(self) -> list[dict]:
        grouped: Dict[int, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for order in self.orders.values():
            if order.status == "open":
                grouped[order.user_id] += order.total
        results = []
        for user_id, amount in grouped.items():
            user = self.users[user_id]
            results.append({"user_id": user_id, "nickname": user.nickname, "outstanding": str(amount)})
        return results

    def quick_fee(self, user_id: int, amount: Decimal, reason: str) -> Order:
        event = self.get_active_event()
        if not event:
            raise ValueError("Geen actief event")
        order_id = self._next("order")
        line = OrderLine(item_id=0, quantity=1, unit_price=amount)
        order = Order(id=order_id, user_id=user_id, event_id=event.id, lines=[line], total=amount, status="open")
        self.orders[order_id] = order
        self._log("settlement.fee", f"Fee {amount} toegevoegd voor user_id={user_id} ({reason})")
        return order

    def create_event(self, name: str) -> Event:
        event = Event(id=self._next("event"), name=name, is_active=False)
        self.events[event.id] = event
        self._log("event.created", f"Event {name} aangemaakt")
        return event

    def activate_event(self, event_id: int) -> Optional[Event]:
        event = self.events.get(event_id)
        if not event:
            return None
        for e in self.events.values():
            e.is_active = False
        event.is_active = True
        self._log("event.activated", f"Event {event.name} actief gezet")
        return event

    def export_event_summary(self, event_id: int) -> dict:
        relevant_orders = [o for o in self.orders.values() if o.event_id == event_id and o.status != "cancelled"]
        sales_by_item: Dict[int, int] = defaultdict(int)
        buyers_by_item: Dict[int, set[int]] = defaultdict(set)
        for order in relevant_orders:
            for line in order.lines:
                if line.item_id == 0:
                    continue
                sales_by_item[line.item_id] += line.quantity
                buyers_by_item[line.item_id].add(order.user_id)

        items = []
        for item_id, sold_qty in sales_by_item.items():
            item = self.items.get(item_id)
            if not item:
                continue
            items.append(
                {
                    "item": item.name,
                    "sold_quantity": sold_qty,
                    "unique_buyers": len(buyers_by_item[item_id]),
                }
            )

        return {
            "event": asdict(self.events[event_id]),
            "items": sorted(items, key=lambda row: row["sold_quantity"], reverse=True),
            "orders": len(relevant_orders),
        }

    def list_logs(self) -> list[dict]:
        return [
            {
                "id": log.id,
                "event_id": log.event_id,
                "actor_user_id": log.actor_user_id,
                "action": log.action,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in sorted(self.logs.values(), key=lambda l: l.id, reverse=True)
        ]
