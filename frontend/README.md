# CertificateGuard AI — Frontend

A React + Vite frontend for the **Deep Learning and Blockchain-Based Academic Certificate Tampering Detection and Verification System**.

It is designed to connect to an existing FastAPI backend that coordinates:
- EfficientNet-B0 certificate image inference
- SHA-256 file hashing
- Ethereum Sepolia smart-contract record lookups

## Requirements

- Node.js 18+ (Node.js 20 LTS recommended)
- npm
- Your Python FastAPI backend running separately

## Run locally

Open a terminal in this directory:

```bash
npm install
```

Copy `.env.example` to `.env` and set the backend URL:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the frontend:

```bash
npm run dev
```

Open the URL printed by Vite, usually `http://localhost:5173`.

Build a production bundle:

```bash
npm run build
npm run preview
```

## Expected backend API

The frontend expects these endpoints:

- `GET /api/health`
- `GET /api/contract-info`
- `GET /api/history`
- `POST /api/verify` — multipart form fields `file` and optional `certificate_id`

`POST /api/verify` should return the actual AI inference and blockchain lookup results. The UI intentionally does not fabricate successful results if the API is unavailable.

The verify response should include fields broadly like:

```json
{
  "success": true,
  "file_name": "certificate.png",
  "certificate_id": "CERT-001",
  "sha256": "actual-sha256",
  "ai": {
    "prediction": "model-returned-class",
    "confidence": 0.93,
    "status": "success"
  },
  "blockchain": {
    "network": "sepolia",
    "record_found": true,
    "hash_matches": true,
    "transaction_hash": null,
    "status": "hash_match"
  },
  "overall_status": "hash_match",
  "message": "Actual backend result"
}
```

This is a response-shape example only, not a real result. Keep the real model class mapping, contract methods, and registration record schema from your existing implementation.

History may be returned as an array or as `{ "items": [...] }` / `{ "history": [...] }`.

## CORS

Configure FastAPI CORS for your local frontend origin, normally `http://localhost:5173`. Do not use unrestricted CORS in production.

## Security notes

- Never put private keys, seed phrases, or Alchemy secret credentials in frontend environment variables.
- Variables prefixed with `VITE_` are bundled into client-side code and must not contain secrets.
- The browser sends uploaded files to the configured backend.
- Use the exact original file when testing a SHA-256 match. Re-encoding or changing even one byte will usually change the hash.
- An AI result is probabilistic. A hash match confirms equality with a registered byte sequence, not that an institution is legitimate.
- This frontend has not been tested against your private backend, model weights, or deployed contract because those artifacts were not provided with this frontend request.

## Troubleshooting

**Backend offline:** Check `VITE_API_BASE_URL`, start FastAPI, and refresh the page.

**CORS error:** Add `http://localhost:5173` to the backend's allowed development origins.

**Hash mismatch:** Test with the exact file used at registration and ensure registration and verification hash the same byte sequence.

**PDF fails:** The backend must implement safe PDF-to-image conversion or explicitly reject PDF files. Do not pass PDF bytes directly to an image-only model.

**Sepolia not confirmed:** Confirm RPC configuration, contract address, ABI, network ID, and read access on the backend.
