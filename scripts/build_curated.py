import sys
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.ocr import extract_fields, DocumentTypeNotSupportedError
from services.mongo import get_collection

CLEAN_DIR = BASE_DIR / "data" / "clean"
CURATED_DIR = BASE_DIR / "data" / "curated"


def build_curated_file(clean_file: Path, batch_id: str):
    with open(clean_file, "r", encoding="utf-8") as f:
        clean_payload = json.load(f)

    text = clean_payload.get("ocr_text_normalized") or clean_payload.get("ocr_text_raw") or ""
    if not text.strip():
        raise ValueError(f"OCR vide dans {clean_file}")

    try:
        extracted = extract_fields(text, include_empty=True)
    except DocumentTypeNotSupportedError:
        extracted = {
            "document_type": clean_payload.get("document_type_hint", "document_inconnu"),
            "numero": None,
            "emetteur": None,
            "siren": None,
            "siret": None,
            "client": None,
            "total_ttc": None,
            "date": None,
            "adresse": None,
            "code_postal": None,
            "ville": None,
            "dates_trouvees": [],
            "lignes": None,
            "sous_total_ht": None,
            "tva_taux": None,
            "tva_montant": None,
            "fournisseur": None,
        }

    out_dir = CURATED_DIR / batch_id
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = clean_file.stem.replace("_ocr", "")
    out_file = out_dir / f"{base_name}_structured.json"

    payload = {
        "document_id": clean_payload["document_id"],
        "source_clean_file": str(clean_file),
        "source_raw_file": clean_payload.get("source_file"),
        "ocr_engine": clean_payload.get("ocr_engine"),
        "document_type_hint": clean_payload.get("document_type_hint"),
        "document_type": extracted.get("document_type"),
        "batch_id": batch_id,
        "extracted_fields": {
            "numero": extracted.get("numero"),
            "emetteur": extracted.get("emetteur"),
            "siren": extracted.get("siren"),
            "siret": extracted.get("siret"),
            "client": extracted.get("client"),
            "total_ttc": extracted.get("total_ttc"),
            "date": extracted.get("date"),
            "adresse": extracted.get("adresse"),
            "code_postal": extracted.get("code_postal"),
            "ville": extracted.get("ville"),
            "dates_trouvees": extracted.get("dates_trouvees"),
            "lignes": extracted.get("lignes"),
            "sous_total_ht": extracted.get("sous_total_ht"),
            "tva_taux": extracted.get("tva_taux"),
            "tva_montant": extracted.get("tva_montant"),
            "fournisseur": extracted.get("fournisseur"),
        },
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    col = get_collection("curated_zone")
    col.update_one({"document_id": payload["document_id"]}, {"$set": payload}, upsert=True)

    print(f"[CURATED] {out_file}")


def process_batch(batch_id: str):
    batch_clean_dir = CLEAN_DIR / batch_id
    if not batch_clean_dir.exists() or not batch_clean_dir.is_dir():
        raise FileNotFoundError(f"Batch clean introuvable: {batch_clean_dir}")

    for clean_file in batch_clean_dir.glob("*_ocr.json"):
        build_curated_file(clean_file, batch_id)


def process_all():
    for clean_file in CLEAN_DIR.rglob("*_ocr.json"):
        batch_id = clean_file.parent.name
        build_curated_file(clean_file, batch_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=False)
    args = parser.parse_args()

    if args.batch_id:
        process_batch(args.batch_id)
    else:
        process_all()