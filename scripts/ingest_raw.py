import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.mongo import get_collection

RAW_DIR = BASE_DIR / "data" / "raw"
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def ingest_raw_file(file_path: Path, batch_id: str):
    stat = file_path.stat()

    payload = {
        "document_id": f"{batch_id}_{file_path.stem}",
        "scenario": batch_id,
        "batch_id": batch_id,
        "filename": file_path.name,
        "file_type": file_path.suffix.lower(),
        "file_size_bytes": stat.st_size,
        "file_path": str(file_path),
        "storage_mode": "filesystem",
        "zone": "raw",
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }

    col = get_collection("raw_zone")
    col.update_one(
        {"document_id": payload["document_id"]},
        {"$set": payload},
        upsert=True,
    )

    print(f"[RAW] {file_path} -> MongoDB raw_zone (metadata only)")


def process_batch(batch_id: str):
    source_clean_dir = RAW_DIR / batch_id / "clean"
    if not source_clean_dir.exists() or not source_clean_dir.is_dir():
        raise FileNotFoundError(f"Batch raw introuvable: {source_clean_dir}")

    for file_path in source_clean_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            ingest_raw_file(file_path, batch_id)


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=False)
    args = parser.parse_args()

    if args.batch_id:
        process_batch(args.batch_id)
    else:
        process_all()