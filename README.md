# CertificateGuard AI — Capstone Project

**Project:** Deep Learning and Blockchain-Based Academic Certificate Tampering Detection and Verification System.

This package brings together the provided React frontend, FastAPI backend, EfficientNet-B0 checkpoint, Ethereum contract ABI, hash reference data, dataset archive, and notebooks.

## Folder map

- `frontend/` — React + Vite web interface.
- `backend/` — FastAPI API, SHA-256 hashing, EfficientNet-B0 inference, and optional read-only Ethereum Sepolia lookup.
- `backend/models/` — trained model checkpoint.
- `backend/data/` — reference hash CSV and record JSON; runtime verification history is generated here.
- `backend/ImageVerification_ABI.json` — smart contract ABI.
- `dataset/capstone_dataset.zip` — supplied dataset archive.
- `notebooks/` — original notebooks kept as reference for dataset creation, training, hashing, and blockchain work.

## Run locally on Windows

### 1. Start backend

Open PowerShell in the `backend` folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit backend/.env and add your own SEPOLIA_RPC_URL if blockchain lookup is needed.
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

First-time install may take a while because PyTorch is a large dependency. If `py -3.11` is not available, install Python 3.10/3.11 and retry.

### 2. Start frontend

Open a second PowerShell window in the `frontend` folder:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Open the local URL printed by Vite, normally `http://localhost:5173`.

## Integration flow

1. The frontend sends the selected certificate to `POST /api/verify`.
2. The backend hashes the exact uploaded bytes with SHA-256.
3. EfficientNet-B0 predicts `Original` or `Tampered` and returns its confidence.
4. The backend queries `getImageRecord(certificate_id)` on the configured contract and compares the stored hash to the uploaded file hash.
5. The frontend displays the AI prediction and blockchain status. If blockchain settings are missing or unreachable, the API reports that status instead of pretending verification succeeded.
6. Verification history is stored locally in `backend/data/verification_history.json`.

API docs: `http://127.0.0.1:8000/docs`

## Important configuration and limitations

- Edit `backend/.env` to provide your own Ethereum Sepolia RPC endpoint. The contract address is prefilled from the supplied notebook; confirm it matches your deployment.
- Do not place private keys, wallet seed phrases, or provider secrets in frontend `.env` files. The frontend environment variables are visible to browser users.
- This project performs read-only blockchain verification; it does not submit registration transactions.
- AI output is a model prediction, not a guarantee of authenticity. A hash match means the uploaded bytes match the bytes registered for that ID.
- For PDF uploads, only the first page is converted to an image for AI inference.
- The notebooks retain their original Colab-oriented cells and paths as research/reference material; the local app uses the backend API instead of requiring notebook cells to run.
- Dataset archive is included as supplied; it is not unpacked automatically.

## Troubleshooting

- **Backend unavailable:** Start backend first and visit `http://127.0.0.1:8000/api/health`.
- **AI dependency/model error:** Ensure all requirements installed in the same active Python environment; the checkpoint is in `backend/models/`.
- **Blockchain unavailable:** Fill `SEPOLIA_RPC_URL` in `backend/.env`, verify internet access and the contract address.
- **CORS error:** Keep frontend at `http://localhost:5173` or add the exact frontend origin to `CORS_ORIGINS`.
- **npm command not found:** Install Node.js 20 LTS and reopen PowerShell.
