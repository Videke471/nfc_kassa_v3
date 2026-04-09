$ErrorActionPreference = "Stop"

Write-Host "[NFC Kassa V3] Windows bootstrap start"

$version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Detected Python version: $version"

if ($version -ge "3.14") {
  Write-Host "Python 3.14 detected. This project currently requires Python 3.12/3.13 because pydantic-core may fail to build on 3.14." -ForegroundColor Yellow
  Write-Host "Install Python 3.12 and recreate the virtualenv:" -ForegroundColor Yellow
  Write-Host "  py -3.12 -m venv .venv"
  exit 1
}

if (!(Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

Write-Host "Bootstrap complete. Start server with:"
Write-Host "python -m uvicorn app.main:app --reload"
