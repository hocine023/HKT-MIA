"""
HKT-MIA Backend — FastAPI
Pipeline : Upload fichiers → OCR (Tesseract) → Extraction regex → Validation LLM (HuggingFace)
"""

import uuid
import json
import tempfile
import os
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.ocr import (
    run_ocr,
    normalize_text,
    extract_fields,
    detect_document_type,
    DocumentTypeNotSupportedError,
)
from services.llm_validator import validate_bundle_with_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="HKT-MIA API",
    description="Pipeline OCR → Extraction → Validation LLM de documents comptables",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Stockage en mémoire ────────────────────────────────────────────────────────
batches: dict[str, dict] = {}


# ── Modèles de réponse (miroir des types TypeScript du front) ─────────────────
class ExtractedFields(BaseModel):
    numero: Optional[str] = None
    emetteur: Optional[str] = None
    siren: Optional[str] = None
    siret: Optional[str] = None
    client: Optional[str] = None
    total_ttc: Optional[float] = None
    date: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    dates_trouvees: Optional[list[str]] = None
    lignes: Optional[list[dict]] = None
    sous_total_ht: Optional[float] = None
    tva_taux: Optional[int] = None
    tva_montant: Optional[float] = None
    fournisseur: Optional[dict] = None


class DocumentData(BaseModel):
    document_id: str
    filename: str
    document_type: str
    ocr_text: Optional[str] = None
    extracted_fields: ExtractedFields


class LLMCheck(BaseModel):
    rule: str
    status: str   # "passed" | "failed" | "not_applicable"
    message: str


class ValidationResult(BaseModel):
    status: str   # "conforme" | "a_verifier" | "non_conforme"
    anomalies: list[str]
    checks: Optional[list[LLMCheck]] = None
    confidence: Optional[float] = None


class ProcessingResult(BaseModel):
    batch_id: str
    documents: list[DocumentData]
    validation: ValidationResult


# ── Helpers ───────────────────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}


def _save_temp_file(content: bytes, filename: str) -> str:
    """Sauvegarde les bytes dans un fichier temporaire et retourne son chemin."""
    ext = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        return tmp.name


def _process_one_file(content: bytes, filename: str) -> DocumentData:
    """OCR + extraction pour un fichier. Retourne un DocumentData."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Format non supporté : {ext}. Acceptés : {', '.join(ALLOWED_EXTENSIONS)}",
        )

    tmp_path = _save_temp_file(content, filename)
    try:
        # 1. OCR
        raw_text = run_ocr(tmp_path)
        clean_text = normalize_text(raw_text)

        # 2. Extraction des champs
        try:
            fields_dict = extract_fields(clean_text, include_empty=True)
        except DocumentTypeNotSupportedError:
            doc_type = detect_document_type(clean_text) or "document_inconnu"
            fields_dict = {"document_type": doc_type}

        doc_type = fields_dict.pop("document_type", "document_inconnu")
        # Retirer raw_text du dict extrait (on le stocke séparément)
        fields_dict.pop("raw_text", None)

        return DocumentData(
            document_id=f"doc_{uuid.uuid4().hex[:6]}",
            filename=filename,
            document_type=doc_type,
            ocr_text=clean_text,
            extracted_fields=ExtractedFields(**{
                k: fields_dict.get(k) for k in ExtractedFields.model_fields
            }),
        )
    finally:
        os.unlink(tmp_path)


def _build_llm_bundle(batch_id: str, documents: list[DocumentData]) -> dict:
    """Construit le bundle attendu par validate_bundle_with_llm."""
    return {
        "scenario_id": batch_id,
        "documents": [
            {
                "document_id": doc.document_id,
                "document_type": doc.document_type,
                "fields": doc.extracted_fields.model_dump(exclude_none=True),
            }
            for doc in documents
        ],
    }


def _llm_result_to_validation(llm_result: dict) -> ValidationResult:
    """Convertit la réponse LLM en ValidationResult."""
    raw_status = llm_result.get("global_status", "a_verifier")
    # Normaliser : le LLM peut retourner "a_verifier" ou "à_vérifier"
    status_map = {
        "conforme": "conforme",
        "a_verifier": "à vérifier",
        "à_vérifier": "à vérifier",
        "non_conforme": "non_conforme",
    }
    status = status_map.get(raw_status, "à vérifier")

    checks = [
        LLMCheck(
            rule=c.get("rule", ""),
            status=c.get("status", "not_applicable"),
            message=c.get("message", ""),
        )
        for c in llm_result.get("checks", [])
    ]

    return ValidationResult(
        status=status,
        anomalies=llm_result.get("anomalies", []),
        checks=checks,
        confidence=llm_result.get("confidence"),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Santé du service."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/upload", response_model=ProcessingResult)
async def upload_documents(files: list[UploadFile] = File(...)):
    """
    Reçoit 1 à N fichiers (PDF, PNG, JPG…).

    Pipeline par fichier :
      1. OCR Tesseract (multi-pipeline, meilleure confiance)
      2. Normalisation texte
      3. Extraction des champs par regex
      4. Validation LLM HuggingFace sur le bundle complet

    Retourne un ProcessingResult compatible avec le front React.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Aucun fichier reçu.")

    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
    documents: list[DocumentData] = []

    # ── Étape 1 & 2 & 3 : OCR + extraction par fichier ────────────────────
    for upload in files:
        content = await upload.read()
        filename = upload.filename or "document"
        logger.info("[%s] Traitement OCR : %s", batch_id, filename)
        doc = _process_one_file(content, filename)
        documents.append(doc)
        logger.info("[%s] Extrait : type=%s siren=%s", batch_id, doc.document_type, doc.extracted_fields.siren)

    # ── Étape 4 : Validation LLM ───────────────────────────────────────────
    logger.info("[%s] Validation LLM (%d documents)…", batch_id, len(documents))
    try:
        bundle = _build_llm_bundle(batch_id, documents)
        llm_result = validate_bundle_with_llm(bundle)
        validation = _llm_result_to_validation(llm_result)
    except Exception as e:
        logger.warning("[%s] LLM indisponible (%s) — fallback règles simples", batch_id, e)
        validation = _fallback_validation(documents)

    result = ProcessingResult(
        batch_id=batch_id,
        documents=documents,
        validation=validation,
    )
    batches[batch_id] = result.model_dump()
    return result


@app.get("/batch/{batch_id}", response_model=ProcessingResult)
def get_batch(batch_id: str):
    """Récupère un résultat de traitement par son batch_id."""
    if batch_id not in batches:
        raise HTTPException(status_code=404, detail="Batch introuvable.")
    return batches[batch_id]


@app.get("/batches", response_model=list[str])
def list_batches():
    """Liste tous les batch_ids en mémoire."""
    return list(batches.keys())


@app.post("/dataset/validate")
async def validate_from_dataset(payload: list[dict]):
    """
    Valide un bundle déjà structuré (ex : issu du pipeline build_curated).
    Attend le même format que validate_bundle_with_llm :
    [{ "document_id": ..., "document_type": ..., "fields": {...} }, ...]

    Utile pour tester le LLM directement sans re-OCR.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Payload vide.")
    bundle = {
        "scenario_id": f"manual_{uuid.uuid4().hex[:6]}",
        "documents": payload,
    }
    try:
        result = validate_bundle_with_llm(bundle)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur LLM : {e}")
    return result


# ── Fallback validation (si LLM indisponible) ─────────────────────────────────
def _fallback_validation(documents: list[DocumentData]) -> ValidationResult:
    """Règles déterministes de secours si le LLM ne répond pas."""
    anomalies: list[str] = []

    sirens = {d.extracted_fields.siren for d in documents if d.extracted_fields.siren}
    if len(sirens) > 1:
        anomalies.append("SIREN incohérent entre les documents du lot")

    sirets = {d.extracted_fields.siret for d in documents if d.extracted_fields.siret}
    if len(sirets) > 1:
        anomalies.append("SIRET incohérent entre les documents du lot")

    for doc in documents:
        if doc.document_type == "facture":
            f = doc.extracted_fields
            if f.sous_total_ht and f.tva_montant and f.total_ttc:
                expected = round(f.sous_total_ht + f.tva_montant, 2)
                if abs(expected - f.total_ttc) > 0.05:
                    anomalies.append(
                        f"[{doc.filename}] TTC incohérent : {f.sous_total_ht} + {f.tva_montant} ≠ {f.total_ttc}"
                    )

    status = "conforme" if not anomalies else ("à vérifier" if len(anomalies) <= 2 else "non_conforme")
    return ValidationResult(
        status=status,
        anomalies=anomalies,
        checks=None,
        confidence=None,
    )
