"""Ingest raw documents into MongoDB raw_zone."""
import sys
import json
import base64
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.mongo import get_collection

RAW_DIR = BASE_DIR / "data" / "raw"
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def ingest_raw_file(file_path: Path, scenario_name: str):
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    payload = {
        "document_id": f"{scenario_name}_{file_path.stem}",
        "scenario": scenario_name,
        "filename": file_path.name,
        "file_type": file_path.suffix.lower(),
        "file_size_bytes": len(file_bytes),
        "file_base64": base64.b64encode(file_bytes).decode("ascii"),
    }

    col = get_collection("raw_zone")
    col.update_one({"document_id": payload["document_id"]}, {"$set": payload}, upsert=True)
    print(f"[RAW] {file_path} -> MongoDB raw_zone")


def process_all():
    for scenario_dir in RAW_DIR.iterdir():
        if not scenario_dir.is_dir():
            continue

        source_clean_dir = scenario_dir / "clean"
        if not source_clean_dir.exists():
            continue

        for file_path in source_clean_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                ingest_raw_file(file_path, scenario_dir.name)


if __name__ == "__main__":
    process_all()
