# CertificateGuard AI — Backend

FastAPI backend connecting the React UI, EfficientNet-B0 model, SHA-256 hashing, and Ethereum Sepolia read-only verification.

## Setup (Windows PowerShell)

1. Install Python 3.10 or 3.11 and Node.js 20 LTS.
2. Open this `backend` folder in a terminal.
3. Create an environment and install packages:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

4. Edit `.env`. For blockchain lookup, set your own Sepolia RPC URL. Never put a private key in this app for verification; lookup is read-only.
5. Start the backend:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/docs` to inspect the API.

## What is connected?

- `POST /api/verify`: SHA-256 of exact uploaded bytes, EfficientNet-B0 inference, and on-chain record lookup.
- `GET /api/health`: backend status.
- `GET /api/contract-info`: configured contract/network status.
- `GET /api/history`: recent local verification history.

Blockchain lookup is intentionally read-only. The API will report blockchain as unavailable if RPC/contract settings are missing or the network cannot be reached; it does not invent successful blockchain results. The AI model checkpoint and contract ABI are included. Model prediction is probabilistic and is not proof that a certificate issuer is legitimate.

## Notes

- The model checkpoint was created for torchvision EfficientNet-B0 with two classes (`Original`, `Tampered`).
- The original dataset archive and notebooks are in the project `dataset/` and `notebooks/` directories.
- For PDFs, only the first page is passed to the model.
