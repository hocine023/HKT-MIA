import os
import uuid
import json
import shutil
from pathlib import Path
from typing import List

import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"

AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080")
AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")
AIRFLOW_DAG_ID = os.getenv("AIRFLOW_DAG_ID", "hkt_mia_pipeline")

app = FastAPI(title="HKT-MIA Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def ensure_dirs():
    (DATA_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "clean").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "curated").mkdir(parents=True, exist_ok=True)


def save_uploaded_files(batch_id: str, files: List[UploadFile]) -> Path:
    batch_raw_clean_dir = RAW_DIR / batch_id / "clean"
    batch_raw_clean_dir.mkdir(parents=True, exist_ok=True)

    for upload in files:
        filename = upload.filename or "document"
        ext = Path(filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail=f"Format non supporté pour {filename}: {ext}"
            )

        out_path = batch_raw_clean_dir / filename
        with open(out_path, "wb") as f:
            shutil.copyfileobj(upload.file, f)

    return batch_raw_clean_dir


def trigger_airflow_dag(batch_id: str) -> dict:
    url = f"{AIRFLOW_BASE_URL}/api/v1/dags/{AIRFLOW_DAG_ID}/dagRuns"
    payload = {"conf": {"batch_id": batch_id}}

    response = requests.post(
        url,
        auth=(AIRFLOW_USERNAME, AIRFLOW_PASSWORD),
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=30,
    )

    if response.status_code >= 300:
        raise HTTPException(
            status_code=502,
            detail=f"Erreur Airflow: {response.status_code} {response.text}"
        )

    return response.json()


def read_validation_file(batch_id: str):
    validation_file = CURATED_DIR / batch_id / "validation_llm.json"
    if not validation_file.exists():
        return None

    with open(validation_file, "r", encoding="utf-8") as f:
        return json.load(f)


def read_structured_documents(batch_id: str):
    scenario_dir = CURATED_DIR / batch_id
    if not scenario_dir.exists():
        return []

    docs = []
    for file_path in scenario_dir.glob("*_structured.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            docs.append(json.load(f))
    return docs


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pipeline/run")
async def pipeline_run(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier reçu")

    ensure_dirs()

    batch_id = f"client_{uuid.uuid4().hex[:8]}"
    save_uploaded_files(batch_id, files)
    dag_run = trigger_airflow_dag(batch_id)

    return {
        "batch_id": batch_id,
        "dag_run_id": dag_run.get("dag_run_id"),
        "status": dag_run.get("state", "queued"),
    }


@app.get("/pipeline/status/{batch_id}")
def pipeline_status(batch_id: str):
    validation = read_validation_file(batch_id)
    documents = read_structured_documents(batch_id)

    status = "running"
    if validation is not None:
        status = "finished"

    return {
        "batch_id": batch_id,
        "status": status,
        "documents_count": len(documents),
        "has_validation": validation is not None,
    }


@app.get("/results")
def get_results():
    ensure_dirs()
    results = []

    if not CURATED_DIR.exists():
        return results

    for batch_dir in CURATED_DIR.iterdir():
        if not batch_dir.is_dir():
            continue

        results.append({
            "batch_id": batch_dir.name,
            "documents": read_structured_documents(batch_dir.name),
            "validation": read_validation_file(batch_dir.name),
        })

    return results


@app.get("/results/{batch_id}")
def get_result(batch_id: str):
    documents = read_structured_documents(batch_id)
    validation = read_validation_file(batch_id)

    if not documents and validation is None:
        raise HTTPException(status_code=404, detail="Résultat introuvable")

    return {
        "batch_id": batch_id,
        "documents": documents,
        "validation": validation,
    }