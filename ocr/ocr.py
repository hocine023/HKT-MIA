import cv2
import logging
import pytesseract
import re
import unicodedata
import json
import os
import numpy as np
from typing import Dict, Optional, Tuple
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

# Constantes OCR
_MIN_IMAGE_HEIGHT = 1500
_OCR_CONFIDENCE_THRESHOLD = 60
_OCR_MIN_TEXT_LENGTH = 20
_MAX_ADDRESS_LENGTH = 120

# ---------------------------------------------------------------------------
# Configuration Tesseract
# ---------------------------------------------------------------------------

def _find_tesseract():
    if os.name != "nt":
        return None
    paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for base in os.environ.get("PATH", "").split(os.pathsep):
        if base and "tesseract" in base.lower():
            exe = os.path.join(base, "tesseract.exe")
            if os.path.exists(exe):
                return exe
    for p in paths:
        if os.path.exists(p):
            return p
    return None

_tesseract_exe = _find_tesseract()
if _tesseract_exe:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_exe

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_tessdata_dir = os.path.join(os.path.dirname(_script_dir), "tessdata")
if os.path.exists(os.path.join(_project_tessdata_dir, "fra.traineddata")):
    os.environ["TESSDATA_PREFIX"] = _project_tessdata_dir + os.sep

# ---------------------------------------------------------------------------
# Prétraitement d'image
# ---------------------------------------------------------------------------

def _pdf_to_images(pdf_path: str, dpi: int = 300) -> list[np.ndarray]:
    pages = convert_from_path(pdf_path, dpi=dpi)
    images = []
    for page in pages:
        img = np.array(page)
        images.append(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return images


def _upscale(image: np.ndarray, min_height: int = _MIN_IMAGE_HEIGHT) -> np.ndarray:
    h = image.shape[0]
    if h < min_height:
        scale = min_height / h
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return image


def _preprocess_pipelines(image: np.ndarray) -> list[np.ndarray]:
    image = _upscale(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    enhanced = cv2.bilateralFilter(enhanced, 9, 75, 75)

    _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )

    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    kernel_sharp = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharp = cv2.filter2D(enhanced, -1, kernel_sharp)
    _, sharp_otsu = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return [otsu, adaptive, denoised, sharp_otsu]

# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def _ocr_confidence(image: np.ndarray, config: str, lang: str = "fra") -> tuple[str, float]:
    data = pytesseract.image_to_data(image, lang=lang, config=config, output_type=pytesseract.Output.DICT)
    words = []
    confidences = []
    for i, conf in enumerate(data["conf"]):
        conf_val = int(conf)
        text = data["text"][i].strip()
        if conf_val > 0 and text:
            words.append(text)
            confidences.append(conf_val)
    text = " ".join(words)
    avg_conf = sum(confidences) / len(confidences) if confidences else 0
    return text, avg_conf


def _best_ocr_from_image(image: np.ndarray) -> str:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    best_text = ""
    best_conf = -1.0

    try:
        text, conf = _ocr_confidence(gray, r"--oem 3 --psm 3")
        if conf > _OCR_CONFIDENCE_THRESHOLD and len(text.strip()) > _OCR_MIN_TEXT_LENGTH:
            return text
        best_text, best_conf = text, conf
    except Exception as e:
        logger.debug("OCR brut échoué: %s", e)

    for img in _preprocess_pipelines(image):
        for cfg in (r"--oem 3 --psm 3", r"--oem 3 --psm 6", r"--oem 3 --psm 4"):
            try:
                t, c = _ocr_confidence(img, cfg)
                if c > best_conf:
                    best_conf = c
                    best_text = t
            except Exception as e:
                logger.debug("OCR pipeline échoué (config=%s): %s", cfg, e)
                continue

    return best_text


def run_ocr(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return "\n".join(_best_ocr_from_image(img) for img in _pdf_to_images(file_path))

    image = cv2.imread(file_path)
    if image is None:
        raise FileNotFoundError(f"Impossible de lire l'image : {file_path}")
    return _best_ocr_from_image(image)

# ---------------------------------------------------------------------------
# Nettoyage du texte
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalise le texte OCR : Unicode NFC, guillemets, espaces."""
    text = text.replace('\x0c', ' ')
    text = unicodedata.normalize('NFC', text)
    # Guillemets et apostrophes typographiques -> ASCII
    text = text.replace('\u00ab', '"').replace('\u00bb', '"')  # « »
    text = text.replace('\u2018', "'").replace('\u2019', "'")  # ' '
    text = re.sub(r'[^\S\n]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.strip() for line in text.splitlines()]
    return '\n'.join(lines).strip()

# ---------------------------------------------------------------------------
# Extraction des champs (documents business : facture, devis, bon de commande)
# ---------------------------------------------------------------------------

def find_all_dates(text: str) -> list[str]:
    patterns = [
        r'\b(\d{2})[/\-\.\s](\d{2})[/\-\.\s](\d{4})\b',
        r'\b(\d{4})[/\-\.\s](\d{2})[/\-\.\s](\d{2})\b',
        r'\b(\d{8})\b',
    ]
    dates = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            groups = match.groups()
            if len(groups) == 1:
                raw = groups[0]
                d, m, y = raw[:2], raw[2:4], raw[4:]
            elif len(groups[0]) == 4:
                y, m, d = groups
            else:
                d, m, y = groups
            try:
                if 1 <= int(d) <= 31 and 1 <= int(m) <= 12 and 1900 <= int(y) <= 2100:
                    formatted = f"{d}/{m}/{y}"
                    if formatted not in seen:
                        seen.add(formatted)
                        dates.append(formatted)
            except ValueError:
                continue
    return dates


def find_document_number(text: str) -> Optional[str]:
    patterns = [
        r'\b(FAC-\d+)\b',
        r'\b(DEV-\d+)\b',
        r'\b(BDC-\d+)\b',
        r'(?:n[°o]?\s*|num[ée]ro\s*[:\s])\s*([A-Z]{2,4}[\-/]?\d{3,})',
        r'(?:facture|devis|commande)\s*(?:n[°o]?\s*)?[:\s]\s*([A-Z0-9\-/]+\d{3,})',
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def find_emetteur(text: str) -> Optional[str]:
    # Match depuis le début de la chaîne ou d'une ligne (multiline)
    match = re.search(r'(?:^|\n)([^\n]+?)\s*SIREN\s*:', text)
    if match:
        candidate = re.sub(r'\s*\|.*$', '', match.group(1)).strip()
        if candidate:
            return candidate
    return None


def find_siren(text: str) -> Optional[str]:
    # Priorité : SIREN/SIRET explicites (contexte fiable)
    match = re.search(r'(?:SIREN|SIRET)\s*[:\s]*(\d[\d\s]{7,16})', text, re.IGNORECASE)
    if match:
        return re.sub(r'\s', '', match.group(1))[:9]
    # Fallback : format SIRET (9+5 chiffres) sans label - évite les faux positifs (prix, quantités)
    match = re.search(r'\b(\d{3}\s?\d{3}\s?\d{3})\s*\d{5}\b', text)
    if match:
        candidate = re.sub(r'\s', '', match.group(1))
        if candidate != "000000000":
            return candidate
    return None


def find_siret(text: str) -> Optional[str]:
    match = re.search(r'SIRET\s*[:\s]*(\d[\d\s]{12,20})', text, re.IGNORECASE)
    if match:
        candidate = re.sub(r'\s', '', match.group(1))[:14]
        if len(candidate) == 14:
            return candidate
    match = re.search(r'\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b', text)
    if match:
        candidate = re.sub(r'\s', '', match.group(1))
        if len(candidate) == 14:
            return candidate
    return None


def _extract_person_name(text_after_label: str) -> Optional[str]:
    match = re.match(
        r'([A-ZÀ-Ýa-zà-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-Ýa-zà-ÿ][a-zà-ÿ]+)*\s+[A-ZÀ-Ý][A-ZÀ-Ý\-]+)',
        text_after_label.strip()
    )
    if match:
        return match.group(1).strip()
    words = text_after_label.strip().split()
    if len(words) >= 2:
        name_parts = []
        for w in words[:3]:
            clean = re.sub(r'[^A-Za-zÀ-ÿ\-]', '', w)
            if clean and clean[0].isupper():
                name_parts.append(clean)
            else:
                break
        if len(name_parts) >= 2:
            return " ".join(name_parts)
    return None


def find_client(text: str) -> Optional[str]:
    labels = [
        "facturer à", "facturé à", "facturer a", "facture à",
        "client :", "client:",
        "responsable:",
        "destinataire", "adressé à",
    ]
    for label in labels:
        idx = text.lower().find(label)
        if idx != -1:
            after = re.sub(r'^[:\s]+', '', text[idx + len(label):]).strip()
            name = _extract_person_name(after)
            if name:
                return name
    return None


def find_total_ttc(text: str) -> Optional[float]:
    patterns = [
        r'total\s*ttc\s*[:\s]*(\d[\d\s]*[.,]\d{2})',
        r'montant\s*ttc\s*[:\s]*(\d[\d\s]*[.,]\d{2})',
        r'net\s*[àa]\s*payer\s*[:\s]*(\d[\d\s]*[.,]\d{2})',
        r'total\s*[:\s]*(\d[\d\s]*[.,]\d{2})\s*€',
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            val = match.group(1).replace(' ', '').replace(',', '.')
            try:
                return float(val)
            except ValueError:
                continue
    return None


def find_document_date(text: str) -> Optional[str]:
    match = re.search(
        r'(?:FAC|DEV|BDC)-\d+\s+Date\s*:\s*(\d{2}[/\-\.\s]\d{2}[/\-\.\s]\d{4})',
        text, re.IGNORECASE
    )
    if match:
        return match.group(1).replace(' ', '/').replace('-', '/').replace('.', '/')

    match = re.search(
        r'(?:FACTURE|DEVIS|BON DE COMMANDE)\s+Date\s*:\s*(\d{2}[/\-\.\s]\d{2}[/\-\.\s]\d{4})',
        text, re.IGNORECASE
    )
    if match:
        return match.group(1).replace(' ', '/').replace('-', '/').replace('.', '/')

    _exclude = ("échéance", "echeance", "validité", "validite", "valide", "livraison", "expir")
    for m in re.finditer(r'Date\s*:\s*(\d{2}[/\-\.\s]\d{2}[/\-\.\s]\d{4})', text, re.IGNORECASE):
        context = text[max(0, m.start() - 30):m.start()].lower()
        if not any(k in context for k in _exclude):
            return m.group(1).replace(' ', '/').replace('-', '/').replace('.', '/')

    dates = find_all_dates(text)
    return dates[0] if dates else None


def find_address(text: str) -> Optional[str]:
    # Pattern : "numéro, type de voie nom, code postal ville" (s'arrête avant Tel:, |, etc.)
    match = re.search(
        r'(\d{1,4}\s*,\s*(?:rue|avenue|av\.?|boulevard|bd|chemin|route|impasse|allée|place|quai|passage|cours|voie)\s+[^,]+,\s*\d{5}\s+[A-Za-zÀ-ÿ\-]+(?:\s+[A-Za-zÀ-ÿ\-]+)*?)\s*(?=Tel:|\||BON DE COMMANDE|FACTURE|DEVIS|Designation|Responsable|Fournisseur|$)',
        text, re.IGNORECASE
    )
    if match:
        addr = match.group(1).strip()
        if len(addr) < _MAX_ADDRESS_LENGTH:
            return addr

    # Fallback : chercher ligne par ligne (si le texte a des retours à la ligne)
    keywords = (
        "rue", "avenue", "av", "boulevard", "bd", "chemin",
        "route", "impasse", "allée", "allee", "place", "quai",
        "passage", "cours", "résidence", "lot", "voie",
    )
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if re.search(r'\b\d{1,4}\b', line) and any(k in low for k in keywords):
            if len(line) < _MAX_ADDRESS_LENGTH:
                return line
    return None


def find_postal_code_and_city(text: str) -> Tuple[Optional[str], Optional[str]]:
    # Mots à tronquer (artefacts OCR collés à la ville : Tel, Fax, etc.)
    _city_suffix_stop = ("tel", "fax", "mobile", "email", "www", "http", "siret", "siren")
    for line in text.splitlines():
        match = re.search(r'\b(\d{5})\s+([A-ZÀ-ÖØ-öø-ÿa-z\- ]{2,})\b', line, re.IGNORECASE)
        if match:
            city = match.group(2).strip().title()
            # Tronquer au premier mot parasite (ex: "Saint Aurélieville Tel" -> "Saint Aurélieville")
            words = city.split()
            for i, w in enumerate(words):
                if w.lower() in _city_suffix_stop:
                    city = " ".join(words[:i]).strip()
                    break
            if city:
                return match.group(1), city
    return None, None

# ---------------------------------------------------------------------------
# Extraction du tableau (factures) : lignes, sous-total HT, TVA
# ---------------------------------------------------------------------------

def find_sous_total_ht(text: str) -> Optional[float]:
    match = re.search(r'sous[- ]?total\s*HT\s*[:\s]*_?\s*(\d[\d\s]*[.,]\d{2})', text, re.IGNORECASE)
    if match:
        val = match.group(1).replace(' ', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            pass
    return None


def find_tva(text: str) -> Optional[float]:
    match = re.search(r'TVA\s*\(\d+\s*%\)\s*[:\s]*(\d[\d\s]*[.,]\d{2})', text, re.IGNORECASE)
    if match:
        val = match.group(1).replace(' ', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            pass
    return None


def find_tva_taux(text: str) -> Optional[int]:
    match = re.search(r'TVA\s*\((\d+)\s*%\)', text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def _parse_decimal(s: str) -> float:
    return float(s.replace(' ', '').replace(',', '.'))


def find_line_items(text: str) -> list:
    """Extrait les lignes du tableau : description, quantité, prix unitaire, total."""
    items = []

    header_match = re.search(r'Total\s*\(EUR\)', text, re.IGNORECASE)
    footer_match = re.search(r'Sous[- ]?total\s*HT', text, re.IGNORECASE)
    if not header_match or not footer_match:
        return items

    zone = text[header_match.end():footer_match.start()]

    zone = re.sub(
        r'Conditions de paiement.*?(?:anticip[ée]\.?|Page\s*\d+)',
        ' ', zone, flags=re.DOTALL | re.IGNORECASE
    )
    zone = re.sub(r'Page\s*\d+', ' ', zone, flags=re.IGNORECASE)
    zone = re.sub(r'\s+', ' ', zone).strip()

    if not zone:
        return items

    # Pattern principal : QTE (entier) + prix_unitaire (décimal) + total (décimal)
    triplet_re = re.compile(r'(\d{1,4})\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})')
    matches = list(triplet_re.finditer(zone))

    if matches:
        last_end = 0
        for m in matches:
            desc = zone[last_end:m.start()].strip()
            desc = re.sub(r'^[\d.,\s]+', '', desc).strip()

            qte = int(m.group(1))
            prix = _parse_decimal(m.group(2))
            total = _parse_decimal(m.group(3))

            items.append({
                "description": desc if desc else None,
                "quantite": qte,
                "prix_unitaire": prix,
                "total": total,
            })
            last_end = m.end()
    else:
        # Fallback : prix + total sans QTE visible (QTE déduit si possible)
        pair_re = re.compile(r'(\d+[.,]\d{2})\s+(\d+[.,]\d{2})')
        last_end = 0
        for m in pair_re.finditer(zone):
            desc = zone[last_end:m.start()].strip()
            desc = re.sub(r'^[\d.,\s]+', '', desc).strip()

            prix = _parse_decimal(m.group(1))
            total = _parse_decimal(m.group(2))
            qte = round(total / prix) if prix > 0 else None

            items.append({
                "description": desc if desc else None,
                "quantite": qte,
                "prix_unitaire": prix,
                "total": total,
            })
            last_end = m.end()

    return items


# ---------------------------------------------------------------------------
# Détection du type de document
# ---------------------------------------------------------------------------

def detect_document_type(text: str) -> str:
    low = text.lower()
    if re.search(r'\bbon\s*de\s*commande\b', low) or re.search(r'\bBDC-\d+', text):
        return "bon_commande"
    if re.search(r'\bdevis\b', low) or re.search(r'\bDEV-\d+', text):
        return "devis"
    if re.search(r'\bfacture\b', low) or re.search(r'\bFAC-\d+', text):
        return "facture"
    return "document_inconnu"

# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class DocumentTypeNotSupportedError(Exception):
    """Levée lorsque le document n'est ni une facture, ni un devis, ni un bon de commande."""
    def __init__(self, doc_type: str):
        self.doc_type = doc_type
        super().__init__(f"Type de document non supporté : {doc_type}. Attendu : facture, devis ou bon_commande.")

# ---------------------------------------------------------------------------
# Assemblage
# ---------------------------------------------------------------------------

_SUPPORTED_DOC_TYPES = ("facture", "devis", "bon_commande")


def extract_fields(text: str, include_empty: bool = False) -> Dict:
    """Extrait les champs du document. Si include_empty=True, tous les champs sont retournés (utile pour évaluation)."""
    doc_type = detect_document_type(text)
    if doc_type not in _SUPPORTED_DOC_TYPES:
        raise DocumentTypeNotSupportedError(doc_type)

    postal_code, city = find_postal_code_and_city(text)

    data = {
        "document_type": doc_type,
        "numero": find_document_number(text),
        "emetteur": find_emetteur(text),
        "siren": find_siren(text),
        "siret": find_siret(text),
        "client": find_client(text),
        "total_ttc": find_total_ttc(text),
        "date": find_document_date(text),
        "adresse": find_address(text),
        "code_postal": postal_code,
        "ville": city,
        "dates_trouvees": find_all_dates(text),
        "raw_text": text,
    }

    if doc_type == "facture":
        lignes = find_line_items(text)
        data["lignes"] = lignes if lignes else None
        data["sous_total_ht"] = find_sous_total_ht(text)
        data["tva_taux"] = find_tva_taux(text)
        data["tva_montant"] = find_tva(text)

    if include_empty:
        return data
    return {k: v for k, v in data.items() if v is not None}


def image_to_json(file_path: str) -> Dict:
    ocr_text = run_ocr(file_path)
    clean_text = normalize_text(ocr_text)
    return extract_fields(clean_text)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Erreur : aucun argument fourni", file=sys.stderr)
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = image_to_json(file_path)
    except DocumentTypeNotSupportedError as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Erreur inattendue : {e}", file=sys.stderr)
        sys.exit(1)

    if output_path is None:
        base = os.path.splitext(os.path.basename(file_path))[0]
        output_path = f"output_{base}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("=== JSON extrait ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n→ Fichier sauvegardé : {output_path}")
