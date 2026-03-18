import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.ocr import run_ocr, normalize_text, detect_document_type
from services.mongo import get_collection

RAW_DIR = BASE_DIR / "data" / "raw"
CLEAN_DIR = BASE_DIR / "data" / "clean"
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def build_clean_file(file_path: Path):
    ocr_text_raw = run_ocr(str(file_path))
    ocr_text_normalized = normalize_text(ocr_text_raw)

    try:
        doc_type_hint = detect_document_type(ocr_text_normalized)
    except Exception:
        doc_type_hint = "document_inconnu"

    # ex: data/raw/scenario_01_normal/clean/facture.pdf
    scenario_dir = file_path.parent.parent.name
    out_dir = CLEAN_DIR / scenario_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / f"{file_path.stem}_ocr.json"

    payload = {
        "document_id": f"{scenario_dir}_{file_path.stem}",
        "source_file": str(file_path),
        "ocr_engine": "tesseract",
        "document_type_hint": doc_type_hint,
        "ocr_text_raw": ocr_text_raw,
        "ocr_text_normalized": ocr_text_normalized
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Store in MongoDB clean_zone
    col = get_collection("clean_zone")
    col.update_one({"document_id": payload["document_id"]}, {"$set": payload}, upsert=True)

    print(f"[CLEAN] {out_file}")


def process_all():
    # On ne prend QUE raw/<scenario>/clean/*
    for scenario_dir in RAW_DIR.iterdir():
        if not scenario_dir.is_dir():
            continue

        source_clean_dir = scenario_dir / "clean"
        if not source_clean_dir.exists() or not source_clean_dir.is_dir():
            continue

        for file_path in source_clean_dir.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            # sécurité supplémentaire : on vérifie que le parent immédiat est bien "clean"
            if file_path.parent.name != "clean":
                continue

            build_clean_file(file_path)


if __name__ == "__main__":
    process_all()