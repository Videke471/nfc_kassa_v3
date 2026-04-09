from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional


@dataclass
class User:
    id: int
    name: str
    nickname: str
    nfc_uid: Optional[str]
    qr_code: Optional[str]
    balance: Decimal
    consumed_total: Decimal = Decimal("0.00")
    is_admin: bool = False
    is_bar_staff: bool = False
    alcohol_allowed: bool = True
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    signed_terms: bool = False
    admin_pin: Optional[str] = None


@dataclass
class Event:
    id: int
    name: str
    is_active: bool = False


@dataclass
class Menu:
    id: int
    name: str
    location: str
    event_id: int
    is_active: bool = False


@dataclass
class Item:
    id: int
    name: str
    price: Decimal
    category: str
    photo_url: str
    contains_alcohol: bool = False
    stock_start: int = 0
    stock_current: int = 0
    menu_id: Optional[int] = None


@dataclass
class OrderLine:
    item_id: int
    quantity: int
    unit_price: Decimal


@dataclass
class Order:
    id: int
    user_id: int
    event_id: int
    lines: list[OrderLine]
    total: Decimal
    status: str = "open"  # open/cancelled/paid
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LogEntry:
    id: int
    event_id: Optional[int]
    actor_user_id: Optional[int]
    action: str
    details: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
