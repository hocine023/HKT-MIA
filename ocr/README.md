# Guide d'installation et d'implémentation — Tesseract OCR

## 1. Installation de Tesseract

### Windows

**Option A — Winget (recommandé)**

```powershell
winget install UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
```

**Option B — Installation manuelle**

1. Télécharger l'installateur : [Tesseract sur GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
2. Exécuter `tesseract-ocr-w64-setup-*.exe`
3. Installer dans `C:\Program Files\Tesseract-OCR\` (chemin par défaut)

### Linux

```bash
# Debian / Ubuntu
sudo apt install tesseract-ocr tesseract-ocr-fra

# Fedora
sudo dnf install tesseract tesseract-langpack-fra
```

### macOS

```bash
brew install tesseract tesseract-lang
```

---

## 2. Pack de langue français

Le script utilise le français (`fra`). Si le pack n'est pas inclus :

- **Windows** : Télécharger [fra.traineddata](https://github.com/tesseract-ocr/tessdata/raw/main/fra.traineddata) et le placer dans `HKT-MIA/tessdata/`
- **Linux/macOS** : Installer le paquet `tesseract-ocr-fra` ou équivalent

---

## 3. Dépendances Python

```bash
pip install opencv-python pytesseract pdf2image numpy
```

**Poppler (requis pour pdf2image sur Windows)** :  
Télécharger depuis [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases) et ajouter `bin/` au PATH, ou installer via conda :

```bash
conda install -c conda-forge poppler
```

---

## 4. Structure du projet

```
HKT-MIA/
├── ocr/
│   ├── ocr.py          # Module OCR (extraction facture, devis, bon de commande)
│   ├── run_dataset.py  # Script batch sur le dataset
│   └── README.md       # Ce guide
├── tessdata/
│   └── fra.traineddata # Pack de langue français
└── dataset/
    └── metadata.json   # Métadonnées du dataset
```

---

## 5. Utilisation

### Un seul fichier

```bash
python ocr/ocr.py chemin/vers/facture.pdf
# → Crée output_facture.json
```

### Traitement du dataset

```bash
# Tout le dataset
python ocr/run_dataset.py

# Filtres
python ocr/run_dataset.py --split test --doc-type facture --limit 5

# 1 fichier aléatoire par (doc_type, split, category)
python ocr/run_dataset.py --sample-one

# Dossier de sortie personnalisé (défaut : ocr_output)
python ocr/run_dataset.py --sample-one --output-dir mes_resultats
```

### En Python

```python
import ocr

result = ocr.image_to_json("dataset/facture/test/legitimate/pdf/fac_leg_pdf_test_0000.pdf")
# → {"document_type": "facture", "numero": "FAC-123", "emetteur": "...", ...}
```

---

## 6. Types de documents supportés

| Type          | Détection                          |
|---------------|------------------------------------|
| Facture       | Mot-clé "facture" ou numéro FAC-   |
| Devis         | Mot-clé "devis" ou numéro DEV-     |
| Bon de commande | Mot-clé "bon de commande" ou BDC- |

Les autres types lèvent `DocumentTypeNotSupportedError`.

---

## 7. Dépannage

**"tesseract is not installed or it's not in your PATH"**  
→ Installer Tesseract et vérifier qu'il est dans le PATH, ou que le script trouve `tesseract.exe` dans les chemins standards.

**"Error opening data file fra.traineddata"**  
→ Placer `fra.traineddata` dans `HKT-MIA/tessdata/`.

**"Unable to get page count. Is poppler installed?"**  
→ Installer Poppler pour la conversion PDF → image.
