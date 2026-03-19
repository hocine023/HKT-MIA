# HKT-MIA — Plateforme d’automatisation documentaire intelligente

## Contexte

Ce projet a été réalisé dans le cadre d’un hackathon autour de l’automatisation du traitement de documents administratifs et comptables.

L’objectif est de reproduire un besoin métier réel :

- un utilisateur dépose plusieurs documents (devis, bon de commande, facture)
- le système les stocke dans une zone brute
- un pipeline documentaire les traite automatiquement
- les informations sont extraites
- une validation intelligente est effectuée
- le résultat est restitué dans deux interfaces simulées :
  - CRM
  - conformité

Le projet repose sur une architecture conteneurisée avec :

- React pour le front-end
- FastAPI pour le back-end
- Apache Airflow pour l’orchestration
- MongoDB pour le stockage des zones de données
- PostgreSQL pour les métadonnées Airflow
- OCR avec Tesseract
- LLM pour la validation documentaire

---

## Objectif métier

Dans un contexte comptable ou conformité, un opérateur doit généralement :

1. recevoir plusieurs documents
2. les lire manuellement
3. extraire les informations utiles
4. vérifier la cohérence entre les pièces
5. détecter les anomalies
6. reporter les résultats dans les outils métiers

Ce projet automatise ce processus.

Exemples de contrôles effectués :

- cohérence du SIREN entre devis et facture
- cohérence du SIRET
- cohérence du client
- cohérence interne de la facture :
  - HT + TVA = TTC
  - somme des lignes = sous-total HT

---

## Architecture globale

Le flux principal du projet est le suivant :

```text
Front-end React
   ↓
Back-end FastAPI
   ↓
Airflow
   ├── ingest_raw
   ├── build_clean
   ├── build_curated
   └── validate_bundle_llm
   ↓
Data Lake + MongoDB
   ↓
Résultats affichés dans le Front
```

### Rôle des composants

#### Front-end
Le front permet :
- l’upload des documents
- l’affichage des documents extraits dans un CRM 
- l’affichage du résultat de validation dans une interface conformité

#### Back-end
Le back :
- reçoit les fichiers déposés par l’utilisateur
- crée un `batch_id`
- stocke les fichiers dans `data/raw/<batch_id>/clean/`
- déclenche le DAG Airflow correspondant
- récupère les résultats finaux
- les expose au front via une API 

#### Airflow
Airflow orchestre le pipeline documentaire :
- ingestion de la zone brute
- OCR et génération de la zone clean
- extraction structurée et génération de la zone curated
- validation intelligente par LLM

#### MongoDB
MongoDB stocke les métadonnées et les résultats dans plusieurs collections :
- `raw_zone`
- `clean_zone`
- `curated_zone`

#### PostgreSQL
PostgreSQL est utilisé par Airflow pour stocker ses métadonnées internes.

---

## Architecture des données

Le projet suit une logique Data Lake en 3 zones :

### 1. Raw zone
Contient les documents bruts :
- PDF
- images

Exemple :
```text
data/raw/client_xxxx/clean/facture.pdf
```

### 2. Clean zone
Contient le résultat OCR :
- texte brut OCR
- texte normalisé
- métadonnées OCR

Exemple :
```json
{
  "document_id": "client_xxxx_facture",
  "source_file": ".../facture.pdf",
  "ocr_engine": "tesseract",
  "document_type_hint": "facture",
  "ocr_text_raw": "...",
  "ocr_text_normalized": "..."
}
```

### 3. Curated zone
Contient les données structurées prêtes à être exploitées :
- type de document
- numéro
- siren / siret
- client
- date
- montants
- lignes
- résultat de validation

Exemple :
```json
{
  "document_type": "facture",
  "extracted_fields": {
    "numero": "FAC-25014",
    "siren": "006720049",
    "siret": "00672004914593",
    "client": "Haithem HENOUDA",
    "date": "19/02/2026",
    "sous_total_ht": 4862.92,
    "tva_taux": 20,
    "tva_montant": 972.58,
    "total_ttc": 5835.50
  }
}
```

---

## Pipeline de traitement

Le pipeline complet est le suivant :

### 1. Upload utilisateur
L’utilisateur charge plusieurs documents via le front.

### 2. Stockage brut
Le back-end enregistre ces documents dans la Raw zone.

### 3. Ingestion Airflow
Airflow déclenche le traitement pour un `batch_id` donné.

### 4. OCR
Les documents sont lus par Tesseract afin d’obtenir un texte exploitable.

### 5. Extraction structurée
Le texte OCR est transformé en JSON métier.

### 6. Validation IA
Le bundle documentaire est transmis à un LLM qui vérifie la cohérence métier.

### 7. Restitution
Les résultats sont affichés :
- dans le CRM simulé
- dans l’outil de conformité

---

## Partie IA

### Positionnement de l’IA
Dans ce projet, l’IA intervient principalement au niveau de la validation documentaire.

Nous n’entraînons pas un modèle from scratch.  
Nous utilisons un LLM pré-entraîné pour faire du raisonnement métier sur des documents déjà structurés.

### Rôle du LLM
Le LLM reçoit un bundle contenant :
- devis
- bon de commande
- facture

sous forme de JSON structurés, puis il produit :
- un statut global
- une liste de checks
- une liste d’anomalies
- un niveau de confiance


## Lancement du projet

### 1. Prérequis
Installer :
- Docker
- Docker Compose

### 2. Variables d’environnement
Créer un fichier `.env` à la racine avec au minimum :

```env
HF_TOKEN=your_huggingface_token
```

### 3. Lancer la stack
```bash
docker compose up --build
```

---

## Accès aux services

Une fois les conteneurs lancés :

- Front-end : `http://localhost:5173`
- Back-end : `http://localhost:8000`
- Health backend : `http://localhost:8000/health`
- Airflow Webserver : `http://localhost:8081`
- Mongo Express : `http://localhost:8082`

---

## Fonctionnement utilisateur

1. Ouvrir l’interface front
2. Ajouter plusieurs documents
3. Lancer le pipeline
4. Le back crée un `batch_id`
5. Airflow orchestre le traitement
6. Les résultats sont produits dans `data/clean` puis `data/curated`
7. Le front affiche :
   - les données extraites dans l’écran CRM
   - le verdict de validation dans l’écran conformité

---


## Stockage MongoDB

Les collections principales utilisées sont :

- `raw_zone`
- `clean_zone`
- `curated_zone`

### Remarque
Les fichiers bruts ne sont pas stockés en base64 dans MongoDB.  
Ils restent sur le système de fichiers dans `data/raw`, tandis que MongoDB conserve uniquement :
- les métadonnées
- les résultats OCR
- les données structurées
- les résultats de validation

---


## Auteur / Projet

Projet réalisé dans le cadre du hackathon HKT-MIA.

Réalisé par : 

AKLI Hocine - HOUDZI Anass - CHEMOUNE Samy - HILLION Erwann -  BEJI Souhir - HENOUDA Haithm - MARCHAND Erwan

lien github : https://github.com/hocine023/HKT-MIA