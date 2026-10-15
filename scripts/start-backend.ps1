Set-Location (Join-Path $PSScriptRoot '..\backend')
if (!(Test-Path '.env')) { Copy-Item '.env.example' '.env' }
if (!(Test-Path '.venv')) { py -3.11 -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
