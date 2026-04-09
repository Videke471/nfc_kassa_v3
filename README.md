# NFC Kassa V3

Deze versie is een uitgebreidere functionele basis voor je gevraagde flow:

## Gebruikersflow
- Login via **NFC kaart** (`/api/auth/login/card`) of **QR code** (`/api/auth/login/qr`).
- Optionele scan-login (`/api/auth/login/scan`) via ACR122U (`pyscard`) of mock (`MOCK_NFC_UID`).
- Bestelscherm met:
  - items (met uitverkocht-status)
  - winkelmandje bekijken en leegmaken
  - bestelling plaatsen vanuit mandje
  - bestelling annuleren
  - saldo + reeds verbruikt saldo opvragen (`/api/user/me`)

## Adminflow
- Admin login met **NFC + pincode** (`/api/auth/admin/login`).
- Dashboard knoppen-model ingebouwd: Users, Afrekenen, Itembeheer, Eventbeheer, Stockbeheer, Export, Logs, Instellingen, Kassa sluiten/afsluiten.
- Users beheer:
  - aanmaken, editen, verwijderen
  - alfabetisch zoeken op naam/nickname
  - tijdelijke QR login genereren (print-ready vlag)
  - gastaccount aanmaken met velden (email, naam, signed terms)
- Afrekenen:
  - openstaande rekeningen per gebruiker
  - snelle fees: +€2.50 (nieuwe lidkaart), +€5.00 (te laat betaald)
- Itembeheer:
  - CRUD items met categorie, foto, alcoholflag en stock
- Eventbeheer:
  - events aanmaken
  - exact 1 actief event tegelijk
  - zonder actief event kan er niet besteld worden
- Export:
  - event samenvatting per item (verkochte aantallen + unieke kopers)
- Logs:
  - acties per event (admin/bar systeemacties)
- Instellingen:
  - bonprinter toggle
- Kassa:
  - open/close state en veilige shutdown endpoint

## Externe bar-pc (Express/Barmanscherm)
Deze backend ondersteunt een aparte pc via HTTP API. Een Express-app kan hierop aansluiten voor live orderoverzicht en bar-readonly functies (openstaand saldo, user verbruik).

## Starten
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open daarna: `http://127.0.0.1:8000`

## Mock scan
```bash
export MOCK_NFC_UID=04AABBCCDD
```

## Testen
```bash
pytest -q
```
