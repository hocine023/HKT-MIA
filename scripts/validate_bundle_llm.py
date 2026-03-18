import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.llm_validator import validate_bundle_with_llm

CURATED_DIR = BASE_DIR / "data" / "curated"


def load_scenario_bundle(scenario_dir: Path) -> dict:
    documents = []

    for file_path in scenario_dir.glob("*_structured.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        documents.append({
            "document_id": payload.get("document_id"),
            "document_type": payload.get("document_type"),
            "fields": payload.get("extracted_fields", {})
        })

    return {
        "scenario_id": scenario_dir.name,
        "documents": documents
    }


def validate_scenario(scenario_dir: Path):
    bundle = load_scenario_bundle(scenario_dir)
    result = validate_bundle_with_llm(bundle)

    output_file = scenario_dir / "validation_llm.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[VALIDATION_LLM] {output_file}")


def process_all():
    for scenario_dir in CURATED_DIR.iterdir():
        if scenario_dir.is_dir():
            validate_scenario(scenario_dir)


if __name__ == "__main__":
    process_all()