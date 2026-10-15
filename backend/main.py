
import os
import io
import csv
import json
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image, ImageOps
import pytesseract
import fitz

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv


# ==================================================
# 1. CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

MODEL_PATH = BASE_DIR / "models" / "efficientnet_b0_certificate_tampering_FINAL.pth"
HASH_CSV_PATH = BASE_DIR / "data" / "image_hashes.csv"
HISTORY_PATH = BASE_DIR / "data" / "verification_history.json"
ABI_PATH = BASE_DIR / "ImageVerification_ABI.json"

TESSERACT_EXE = os.getenv(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)
pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CertificateGuard")

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

app = FastAPI(
    title="CertificateGuard API",
    description="AI, OCR, file hash and blockchain certificate verification",
    version="1.2.0",
)

cors_origins = [
    item.strip()
    for item in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if item.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


# ==================================================
# 2. LOAD AI MODEL
# ==================================================

model = None
model_error = None

IMAGE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


def load_classifier():
    global model, model_error

    if model is not None:
        return model

    if not MODEL_PATH.exists():
        model_error = f"Model file not found: {MODEL_PATH}"
        logger.error(model_error)
        return None

    try:
        checkpoint = torch.load(
            MODEL_PATH,
            map_location=DEVICE,
            weights_only=False,
        )

        if isinstance(checkpoint, dict):
            state_dict = (
                checkpoint.get("model_state_dict")
                or checkpoint.get("state_dict")
                or checkpoint.get("model")
                or checkpoint
            )
        else:
            state_dict = checkpoint

        if not isinstance(state_dict, dict):
            raise ValueError("Unsupported model checkpoint format.")

        state_dict = {
            key.removeprefix("module."): value
            for key, value in state_dict.items()
        }

        candidate = models.efficientnet_b0(weights=None)
        in_features = candidate.classifier[1].in_features
        candidate.classifier[1] = nn.Linear(in_features, 2)

        candidate.load_state_dict(state_dict, strict=True)
        candidate.to(DEVICE)
        candidate.eval()

        model = candidate
        model_error = None
        logger.info("EfficientNet-B0 loaded successfully.")

        return model

    except Exception as exc:
        model_error = str(exc)
        logger.exception("Model loading failed")
        return None


def classify_certificate(image: Image.Image) -> dict:
    classifier = load_classifier()

    if classifier is None:
        return {
            "prediction": "Unavailable",
            "confidence": None,
            "model_status": "error",
            "model_error": model_error,
        }

    try:
        image = ImageOps.exif_transpose(image).convert("RGB")
        tensor = IMAGE_TRANSFORM(image).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            probabilities = torch.softmax(
                classifier(tensor), dim=1
            )[0]

        predicted_index = int(torch.argmax(probabilities).item())
        confidence = float(probabilities[predicted_index].item())

        # These labels must match the order used during model training.
        labels = ["Original", "Tampered"]

        return {
            "prediction": labels[predicted_index],
            "confidence": round(confidence, 4),
            "model_status": "success",
            "model_error": None,
        }

    except Exception as exc:
        logger.exception("Classification failed")
        return {
            "prediction": "Unavailable",
            "confidence": None,
            "model_status": "error",
            "model_error": str(exc),
        }


# ==================================================
# 3. SHA-256 HASH
# ==================================================

def calculate_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


# ==================================================
# 4. OCR AND FIELD EXTRACTION
# ==================================================

def extract_named_fields(text: str) -> dict:
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    result = {
        "student_name": None,
        "certificate_id": None,
        "course_name": None,
        "issue_date": None,
        "institution": None,
    }

    def find_value(patterns):
        for line in lines:
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)

                if match:
                    value = match.group(1).strip(" :#-|")

                    if value:
                        return value[:200]

        return None

    # Student name: handles a name appearing on the same line
    # as the registration number.
    result["student_name"] = find_value([
        r"\bname\s*:\s*(.+?)(?=\s+(?:admitted year|programme|program|term)\s*:|$)",
        r"^\s*(?:student\s*name|name\s*of\s*(?:the\s*)?(?:student|recipient))\s*[:\-]\s*(.+)$",
        r"^\s*(?:awarded\s*to|presented\s*to)\s*[:\-]?\s*(.+)$",
    ])

    # Certificate/registration number.
    # Supports OCR text such as "ieg.No: 23BCE20239".
    result["certificate_id"] = find_value([
        r"\b(?:reg|ieg)\s*\.?\s*no\s*\.?\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/\-]*)",
        r"\b(?:registration|certificate)\s*(?:id|no\.?|number)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/\-]*)",
        r"\bcredential\s*id\s*[:#\-]?\s*([A-Z0-9][A-Z0-9/\-]*)",
    ])

    # Course or programme.
    result["course_name"] = find_value([
        r"^\s*(?:programme|program)\s*&\s*branch\s*:\s*(.+)$",
        r"^\s*(?:course|programme|program|qualification)\s*(?:name)?\s*:\s*(.+)$",
    ])

    # Issue date: avoid matching unrelated dates unless labelled Date.
    result["issue_date"] = find_value([
        r"\b(?:date\s*of\s*issue|issued\s*on|issue\s*date|date\s*issued)\s*[:\-]\s*(.+)$",
        r"^\s*date\s*:\s*(\d{1,2}[-/ ][A-Za-z]{3,9}[-/ ]\d{4})\b",
    ])

    # Prefer a complete institution name rather than the word "UNIVERSITY".
    result["institution"] = find_value([
        r"^\s*(?:institution|university|college|organization|organisation)\s*:\s*(.+)$",
    ])

    if not result["institution"]:
        for line in lines:
            if re.search(
                r"\bVIT[- ]?AP\s+University\b",
                line,
                re.IGNORECASE,
            ):
                result["institution"] = "VIT-AP University"
                break

    if not result["institution"]:
        for line in lines:
            if re.search(
                r"\b[A-Z][A-Za-z&.' -]+\s+(?:University|College)\b",
                line,
            ) and len(line.split()) >= 2:
                result["institution"] = line[:200]
                break

    return result


def extract_certificate_details(
    file_bytes: bytes,
    filename: str,
) -> dict:
    try:
        extracted_text = []
        extension = Path(filename).suffix.lower()

        if extension == ".pdf":
            with fitz.open(
                stream=file_bytes,
                filetype="pdf",
            ) as pdf:
                for page in pdf:
                    page_text = page.get_text("text").strip()

                    if not page_text:
                        pixmap = page.get_pixmap(
                            matrix=fitz.Matrix(2, 2),
                            alpha=False,
                        )
                        page_image = Image.open(
                            io.BytesIO(pixmap.tobytes("png"))
                        ).convert("RGB")

                        page_text = pytesseract.image_to_string(
                            page_image,
                            lang="eng",
                        ).strip()

                    if page_text:
                        extracted_text.append(page_text)

        else:
            image = Image.open(
                io.BytesIO(file_bytes)
            )
            image = ImageOps.exif_transpose(image).convert("RGB")

            text = pytesseract.image_to_string(
                image,
                lang="eng",
            ).strip()

            if text:
                extracted_text.append(text)

        full_text = "\n".join(extracted_text).strip()

        return {
            "ocr_status": "success",
            "ocr_text": full_text,
            "ocr_error": None,
            "details": extract_named_fields(full_text),
        }

    except Exception as exc:
        logger.exception("OCR extraction failed")

        return {
            "ocr_status": "error",
            "ocr_text": "",
            "ocr_error": str(exc),
            "details": {
                "student_name": None,
                "certificate_id": None,
                "course_name": None,
                "issue_date": None,
                "institution": None,
            },
        }


# ==================================================
# 5. FIELD ANALYSIS
# ==================================================

def build_field_analysis(details: dict) -> dict:
    fields = {}

    for field, value in details.items():
        fields[field] = {
            "value": value,
            "status": "needs_reference" if value else "not_extracted",
            "message": (
                "Compare with trusted certificate records."
                if value
                else "Could not reliably extract this field."
            ),
        }

    return {
        "fields": fields,
        "tampered_fields": [],
        "reference_comparison_available": False,
    }


# ==================================================
# 6. LOCAL HASH DATABASE
# ==================================================

def lookup_hash_record(file_hash: str) -> dict:
    if not HASH_CSV_PATH.exists():
        return {
            "found": False,
            "status": "database_unavailable",
            "certificate_id": None,
        }

    try:
        with open(
            HASH_CSV_PATH,
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            for row in reader:
                normalized = {
                    str(key).strip().lower(): value
                    for key, value in row.items()
                    if key is not None
                }

                stored_hash = (
                    normalized.get("sha256")
                    or normalized.get("hash")
                    or normalized.get("image_hash")
                    or normalized.get("file_hash")
                )

                if (
                    stored_hash
                    and stored_hash.strip().lower() == file_hash.lower()
                ):
                    certificate_id = (
                        normalized.get("certificate_id")
                        or normalized.get("certificate id")
                        or normalized.get("id")
                    )

                    return {
                        "found": True,
                        "status": "hash_match",
                        "certificate_id": certificate_id,
                    }

        return {
            "found": False,
            "status": "hash_not_found",
            "certificate_id": None,
        }

    except Exception as exc:
        logger.exception("Hash database lookup failed")

        return {
            "found": False,
            "status": "database_error",
            "certificate_id": None,
            "error": str(exc),
        }


# ==================================================
# 7. BLOCKCHAIN LOOKUP (READ ONLY)
# ==================================================

def get_blockchain_record(
    certificate_id: str | None,
    uploaded_hash: str,
) -> dict:
    rpc_url = os.getenv("SEPOLIA_RPC_URL")
    contract_address = os.getenv("CONTRACT_ADDRESS")

    if not rpc_url or not contract_address:
        return {
            "status": "unavailable",
            "record_found": False,
            "hash_matches": None,
            "message": "Check SEPOLIA_RPC_URL and CONTRACT_ADDRESS in backend/.env.",
        }

    if not certificate_id:
        return {
            "status": "not_checked",
            "record_found": False,
            "hash_matches": None,
            "message": "No certificate ID is available for blockchain lookup.",
        }

    if not ABI_PATH.exists():
        return {
            "status": "unavailable",
            "record_found": False,
            "hash_matches": None,
            "message": "ImageVerification_ABI.json was not found.",
        }

    try:
        from web3 import Web3

        web3 = Web3(
            Web3.HTTPProvider(
                rpc_url,
                request_kwargs={"timeout": 10},
            )
        )

        if not web3.is_connected():
            return {
                "status": "unavailable",
                "record_found": False,
                "hash_matches": None,
                "message": "Could not connect to the RPC endpoint.",
            }

        if web3.eth.chain_id != 11155111:
            return {
                "status": "unavailable",
                "record_found": False,
                "hash_matches": None,
                "message": "RPC endpoint is not connected to Sepolia.",
            }

        with open(ABI_PATH, "r", encoding="utf-8") as abi_file:
            abi_data = json.load(abi_file)

        abi = (
            abi_data.get("abi", abi_data)
            if isinstance(abi_data, dict)
            else abi_data
        )

        address = Web3.to_checksum_address(contract_address)

        if not web3.eth.get_code(address):
            return {
                "status": "unavailable",
                "record_found": False,
                "hash_matches": None,
                "message": "No deployed contract bytecode found at this address.",
            }

        contract = web3.eth.contract(
            address=address,
            abi=abi,
        )

        record = contract.functions.getImageRecord(
            certificate_id
        ).call()

        stored_hash, prediction, confidence_bps, timestamp, exists = record

        if not exists:
            return {
                "status": "not_registered",
                "network": "sepolia",
                "certificate_id": certificate_id,
                "record_found": False,
                "hash_matches": None,
                "message": "No blockchain record exists for this certificate ID.",
                "record": None,
            }

        if isinstance(stored_hash, (bytes, bytearray)):
            stored_hash_hex = bytes(stored_hash).hex()
        else:
            stored_hash_hex = str(stored_hash).removeprefix("0x")

        uploaded_hash_normalized = uploaded_hash.lower().removeprefix("0x")
        hash_matches = (
            stored_hash_hex.lower() == uploaded_hash_normalized
        )

        return {
            "status": "record_found",
            "network": "sepolia",
            "certificate_id": certificate_id,
            "record_found": True,
            "hash_matches": hash_matches,
            "message": (
                "Uploaded file hash matches the registered blockchain hash."
                if hash_matches
                else "A record exists, but its hash differs from the uploaded file."
            ),
            "record": {
                "sha256_hash": stored_hash_hex,
                "prediction": prediction,
                "confidence_bps": int(confidence_bps),
                "confidence": int(confidence_bps) / 10000,
                "timestamp": int(timestamp),
            },
        }

    except Exception as exc:
        logger.exception("Blockchain lookup failed")

        return {
            "status": "unavailable",
            "record_found": False,
            "hash_matches": None,
            "message": (
                f"Blockchain lookup failed: {type(exc).__name__}: "
                f"{str(exc)[:250]}"
            ),
        }


# ==================================================
# 8. VERIFICATION HISTORY
# ==================================================

def save_history(record: dict) -> None:
    try:
        history = []

        if HISTORY_PATH.exists():
            with open(
                HISTORY_PATH,
                "r",
                encoding="utf-8",
            ) as history_file:
                existing = json.load(history_file)

                if isinstance(existing, list):
                    history = existing

        history.insert(0, record)
        history = history[:500]

        with open(
            HISTORY_PATH,
            "w",
            encoding="utf-8",
        ) as history_file:
            json.dump(history, history_file, indent=2, default=str)

    except Exception:
        logger.exception("Could not save verification history")


# ==================================================
# 9. API ROUTES
# ==================================================

@app.get("/")
def root():
    return {
        "message": "CertificateGuard API is running",
        "status": "success",
    }


@app.get("/api/health")
def health():
    return {
        "status": "success",
        "ocr_executable_exists": Path(TESSERACT_EXE).exists(),
        "model_file_exists": MODEL_PATH.exists(),
        "device": str(DEVICE),
    }


@app.post("/api/verify")
async def verify_certificate(
    file: UploadFile = File(...),
    certificate_id: str | None = Form(default=None),
):
    filename = file.filename or "certificate"
    extension = Path(filename).suffix.lower()

    allowed_extensions = {
        ".png", ".jpg", ".jpeg", ".webp",
        ".bmp", ".tif", ".tiff", ".pdf",
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Upload an image or PDF.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Maximum upload size is 20 MB.",
        )

    file_hash = calculate_sha256(file_bytes)

    try:
        if extension == ".pdf":
            with fitz.open(
                stream=file_bytes,
                filetype="pdf",
            ) as pdf:
                if len(pdf) == 0:
                    raise ValueError("PDF contains no pages.")

                pixmap = pdf[0].get_pixmap(
                    matrix=fitz.Matrix(2, 2),
                    alpha=False,
                )

                classification_image = Image.open(
                    io.BytesIO(pixmap.tobytes("png"))
                ).convert("RGB")

        else:
            classification_image = Image.open(
                io.BytesIO(file_bytes)
            ).convert("RGB")

        classification = classify_certificate(classification_image)

    except Exception as exc:
        logger.exception("Uploaded file could not be read")

        raise HTTPException(
            status_code=400,
            detail=f"Could not read uploaded certificate: {exc}",
        )

    ocr_result = extract_certificate_details(file_bytes, filename)
    field_analysis = build_field_analysis(ocr_result["details"])
    hash_record = lookup_hash_record(file_hash)

    supplied_id = (certificate_id or "").strip()

    # Ignore Swagger's example placeholder.
    if supplied_id.lower() == "string":
        supplied_id = ""

    resolved_certificate_id = (
        supplied_id
        or hash_record.get("certificate_id")
        or ocr_result["details"].get("certificate_id")
    )

    blockchain_result = get_blockchain_record(
        resolved_certificate_id,
        file_hash,
    )

    response = {
        "status": "success",
        "filename": filename,
        "prediction": classification["prediction"],
        "confidence": classification["confidence"],
        "model_status": classification["model_status"],
        "model_error": classification.get("model_error"),
        "sha256": file_hash,
        "hash_match": hash_record["found"],
        "hash_database": hash_record,
        "ocr_status": ocr_result["ocr_status"],
        "ocr_text": ocr_result["ocr_text"],
        "ocr_error": ocr_result["ocr_error"],
        "details": ocr_result["details"],
        "field_analysis": field_analysis,
        "tampered_fields": field_analysis["tampered_fields"],
        "blockchain": blockchain_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    save_history(response)
    return response


@app.get("/api/history")
def get_history():
    if not HISTORY_PATH.exists():
        return {
            "status": "success",
            "history": [],
        }

    try:
        with open(
            HISTORY_PATH,
            "r",
            encoding="utf-8",
        ) as history_file:
            history = json.load(history_file)

        if not isinstance(history, list):
            history = []

        return {
            "status": "success",
            "history": history,
        }

    except Exception as exc:
        logger.exception("Could not read verification history")

        raise HTTPException(
            status_code=500,
            detail=f"Could not read verification history: {exc}",
        )
