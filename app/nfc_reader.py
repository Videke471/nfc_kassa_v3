from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class NFCScanResult:
    uid: str
    source: str


class NFCReader:
    def scan_uid(self) -> Optional[NFCScanResult]:
        raise NotImplementedError


class MockNFCReader(NFCReader):
    """Voor ontwikkeling zonder hardware: leest MOCK_NFC_UID env var."""

    def scan_uid(self) -> Optional[NFCScanResult]:
        uid = os.getenv("MOCK_NFC_UID")
        if not uid:
            return None
        return NFCScanResult(uid=uid.strip().upper(), source="mock")


class ACR122UReader(NFCReader):
    """Basale ACR122U-lezer via pyscard; valt terug naar None als pyscard ontbreekt."""

    def __init__(self) -> None:
        try:
            from smartcard.System import readers  # type: ignore
        except Exception:  # noqa: BLE001
            self._readers = None
            return

        self._readers = readers

    def scan_uid(self) -> Optional[NFCScanResult]:
        if self._readers is None:
            return None

        try:
            available = self._readers()
            if not available:
                return None

            connection = available[0].createConnection()
            connection.connect()
            # APDU command: get UID
            data, _sw1, _sw2 = connection.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
            uid = "".join(f"{byte:02X}" for byte in data)
            if not uid:
                return None
            return NFCScanResult(uid=uid, source="acr122u")
        except Exception:  # noqa: BLE001
            return None
