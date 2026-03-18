# HKT-MIA — Backend

API FastAPI qui branche directement sur les services `ocr.py` et `llm_validator.py` existants.

## Pipeline

```
POST /upload  (PDF / PNG / JPG)
      │
      ▼
  run_ocr()           ← services/ocr.py  (Tesseract, multi-pipeline)
      │
  normalize_text()
      │
  extract_fields()    ← regex SIREN, SIRET, montants, lignes…
      │
  validate_bundle_with_llm()  ← services/llm_validator.py  (HuggingFace)
      │
      ▼
  ProcessingResult    → front React
```

## Installation

```bash
# 1. Dépendances système
# Ubuntu/Debian :
sudo apt install tesseract-ocr tesseract-ocr-fra poppler-utils

# Windows : installer Tesseract + Poppler, mettre les chemins dans .env

# 2. Python
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env
# → Renseigner HF_TOKEN et POPPLER_PATH (Windows)
```

## Lancer

```bash
uvicorn main:app --reload --port 8000
```

API : http://localhost:8000  
Docs : http://localhost:8000/docs

## Endpoints

| Méthode | URL | Description |
|---------|-----|-------------|
| `GET`  | `/health` | Santé du service |
| `POST` | `/upload` | Upload fichiers → ProcessingResult complet |
| `GET`  | `/batch/{id}` | Récupère un résultat par batch_id |
| `GET`  | `/batches` | Liste tous les batch_ids |
| `POST` | `/dataset/validate` | Valide un bundle structuré sans re-OCR |

## Brancher le frontend

Dans `UploadPage.tsx`, remplacer le `setTimeout` mock par :

```typescript
const handleProcess = async (files: FileList) => {
  setLoading(true);
  const formData = new FormData();
  Array.from(files).forEach(f => formData.append('files', f));

  const res = await fetch('http://localhost:8000/upload', {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) throw new Error(await res.text());
  const batch = await res.json();

  setBatch(batch);
  setLoading(false);
  navigate('/crm');
};
```

Le `ProcessingResult` retourné est compatible avec les types TypeScript existants.

## Structure du projet

```
hkt-mia-backend/
├── main.py                  ← API FastAPI
├── requirements.txt
├── .env.example
├── services/
│   ├── __init__.py
│   ├── ocr.py               ← OCR + extraction regex (inchangé)
│   └── llm_validator.py     ← Validation LLM HuggingFace (inchangé)
```

## Fallback si LLM indisponible

Si `HF_TOKEN` est absent ou que le LLM ne répond pas, le back bascule automatiquement
sur un validateur déterministe (cohérence SIREN/SIRET, calcul TTC vs HT+TVA).
Le front reçoit quand même un `ProcessingResult` valide.
