# NFC Kassa V3

Deze versie is een uitgebreidere functionele basis voor je gevraagde flow.

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

## Installatie & opstarten

### Linux/macOS (bash/zsh)
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Windows CMD
```bat
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open daarna: `http://127.0.0.1:8000`

## Mock scan
Linux/macOS:
```bash
export MOCK_NFC_UID=04AABBCCDD
```

Windows PowerShell:
```powershell
$env:MOCK_NFC_UID = "04AABBCCDD"
```

Windows CMD:
```bat
set MOCK_NFC_UID=04AABBCCDD
```

## Testen
Linux/macOS:
```bash
pytest -q
```

Windows (PowerShell/CMD):
```powershell
python -m pytest -q
```


## Troubleshooting (Windows)
Als je bij `uvicorn app.main:app --reload` deze fout krijgt:
`ModuleNotFoundError: No module named 'fastapi'`, gebruik dan exact dit:

```powershell
# 1) check Python versie (aanbevolen: 3.11 of 3.12)
python --version

# 2) activeer virtualenv opnieuw
.\.venv\Scripts\Activate.ps1

# 3) installeer dependencies met dezelfde interpreter
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4) controleer of fastapi echt in deze venv zit
python -m pip show fastapi

# 5) start uvicorn via python -m (zelfde interpreter)
python -m uvicorn app.main:app --reload
```

> Belangrijk: Python 3.14 kan sneller compatibiliteitsproblemen geven bij sommige packages. 
> Als installatie blijft falen, gebruik Python 3.12 en maak de venv opnieuw aan.
