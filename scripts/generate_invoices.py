import csv
import random
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

fake = Faker("fr_FR")
random.seed(42)
Faker.seed(42)



COLLEGUES = [
    {"prenom": "Hocine", "nom": "AKLI"},
    {"prenom": "Anass", "nom": "HOUDZI"},
    {"prenom": "Samy", "nom": "CHEMOUNE"},
    {"prenom": "Erwann", "nom": "HILLION"},
    {"prenom": "Souhir", "nom": "BEJI"},
    {"prenom": "Haithem", "nom": "HENOUDA"},
    {"prenom": "Erwan", "nom": "MARCHAND"},
]

SIREN_CSV = Path(__file__).parent / "StockUniteLegale_utf8.csv"
REAL_COMPANIES = []


def load_siren_data(n=200):
    global REAL_COMPANIES
    print(f"Chargement de {n} entreprises depuis {SIREN_CSV}...")
    count = 0
    with open(SIREN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (
                row.get("etatAdministratifUniteLegale") == "A"
                and row.get("denominationUniteLegale")
                and row.get("siren")
                and len(row["siren"]) == 9
            ):
                REAL_COMPANIES.append(
                    {
                        "siren": row["siren"],
                        "denomination": row["denominationUniteLegale"],
                        "categorie_juridique": row.get("categorieJuridiqueUniteLegale", ""),
                        "activite": row.get("activitePrincipaleUniteLegale", ""),
                    }
                )
                count += 1
                if count >= n:
                    break
    print(f"  -> {len(REAL_COMPANIES)} entreprises chargées.")


def get_random_company():
    return random.choice(REAL_COMPANIES)


def generate_siret(siren):
    nic = f"{random.randint(1, 99999):05d}"
    return f"{siren}{nic}"


def random_collegue():
    c = random.choice(COLLEGUES)
    return f"{c['prenom']} {c['nom']}"


def sanitize(text):
    return str(text).encode("latin-1", errors="replace").decode("latin-1")


# PDF
class InvoicePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


# GENERATION FACTURE
def generate_invoice_data(legitimate=True, scenario="normal"):
    emetteur = get_random_company()
    client_name = random_collegue()

    date_facture = fake.date_between(start_date="-45d", end_date="today")
    date_echeance = date_facture + timedelta(days=random.choice([30, 45, 60, 90]))

    nb_lignes = random.randint(1, 6)
    lignes = []
    for _ in range(nb_lignes):
        desc = fake.bs().capitalize()
        qte = random.randint(1, 20)
        prix_unitaire = round(random.uniform(10, 500), 2)
        total_ligne = round(qte * prix_unitaire, 2)
        lignes.append(
            {
                "description": desc,
                "quantite": qte,
                "prix_unitaire": prix_unitaire,
                "total": total_ligne,
            }
        )

    sous_total = round(sum(l["total"] for l in lignes), 2)
    taux_tva = 0.20
    tva = round(sous_total * taux_tva, 2)
    total_ttc = round(sous_total + tva, 2)

    siren = emetteur["siren"]
    siret = generate_siret(siren)

    invoice = {
        "doc_type": "facture",
        "numero": f"FAC-{fake.unique.random_int(min=10000, max=99999)}",
        "date": date_facture.strftime("%d/%m/%Y"),
        "date_echeance": date_echeance.strftime("%d/%m/%Y"),
        "emetteur": {
            "nom": emetteur["denomination"],
            "siren": siren,
            "siret": siret,
            "adresse": fake.address().replace("\n", ", "),
            "telephone": fake.phone_number(),
            "email": fake.company_email(),
        },
        "client": {
            "nom": client_name,
            "adresse": fake.address().replace("\n", ", "),
            "email": fake.email(),
        },
        "lignes": lignes,
        "sous_total": sous_total,
        "taux_tva": taux_tva,
        "tva": tva,
        "total_ttc": total_ttc,
        "legitimate": True,
        "scenario": "normal",
        "falsifications": [],
    }

    if not legitimate:
        invoice["legitimate"] = False
        invoice["scenario"] = scenario
        falsifications = []

        if scenario == "siren_mismatch":
            fake_siren = f"{random.randint(100000000, 999999999)}"
            invoice["emetteur"]["siren"] = fake_siren
            invoice["emetteur"]["siret"] = generate_siret(fake_siren)
            falsifications.append("SIREN ne correspond pas à l'entreprise")

        elif scenario == "date_incoherente":
            date_ech_fausse = date_facture - timedelta(days=random.randint(10, 90))
            invoice["date_echeance"] = date_ech_fausse.strftime("%d/%m/%Y")
            falsifications.append("Date d'échéance antérieure à la date de facture")

        elif scenario == "entreprise_fictive":
            invoice["emetteur"]["nom"] = fake.company()
            invoice["emetteur"]["siren"] = f"{random.randint(100000000, 999999999)}"
            invoice["emetteur"]["siret"] = generate_siret(invoice["emetteur"]["siren"])
            falsifications.append("Entreprise fictive avec faux SIREN")

        elif scenario == "expire":
            old_date = fake.date_between(start_date="-10y", end_date="-5y")
            invoice["date"] = old_date.strftime("%d/%m/%Y")
            invoice["date_echeance"] = (old_date + timedelta(days=30)).strftime("%d/%m/%Y")
            falsifications.append("Document expiré (date très ancienne)")

        invoice["falsifications"] = falsifications

    return invoice


def render_invoice_pdf(invoice, output_path):
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, sanitize(invoice["emetteur"]["nom"]), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(f"SIREN: {invoice['emetteur']['siren']}  |  SIRET: {invoice['emetteur']['siret']}"), ln=True)
    pdf.cell(0, 5, sanitize(invoice["emetteur"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(f"Tel: {invoice['emetteur']['telephone']}  |  {invoice['emetteur']['email']}"), ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "FACTURE", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 6, f"N° Facture: {invoice['numero']}")
    pdf.cell(95, 6, f"Date: {invoice['date']}", ln=True)
    pdf.cell(95, 6, f"Date d'échéance: {invoice['date_echeance']}", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Facturer à :", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(invoice["client"]["nom"]), ln=True)
    pdf.cell(0, 5, sanitize(invoice["client"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(invoice["client"]["email"]), ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    col_widths = [80, 25, 35, 40]
    headers = ["Description", "Qte", "Prix unit. (EUR)", "Total (EUR)"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    for ligne in invoice["lignes"]:
        pdf.cell(col_widths[0], 7, sanitize(ligne["description"][:40]), border=1)
        pdf.cell(col_widths[1], 7, str(ligne["quantite"]), border=1, align="C")
        pdf.cell(col_widths[2], 7, f"{ligne['prix_unitaire']:.2f}", border=1, align="R")
        pdf.cell(col_widths[3], 7, f"{ligne['total']:.2f}", border=1, align="R")
        pdf.ln()

    pdf.ln(5)
    x_label = 120
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(x_label)
    pdf.cell(45, 7, "Sous-total HT:", align="R")
    pdf.cell(30, 7, f"{invoice['sous_total']:.2f} EUR", align="R", ln=True)
    pdf.set_x(x_label)
    pdf.cell(45, 7, f"TVA ({int(invoice['taux_tva']*100)}%):", align="R")
    pdf.cell(30, 7, f"{invoice['tva']:.2f} EUR", align="R", ln=True)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_x(x_label)
    pdf.cell(45, 8, "Total TTC:", align="R")
    pdf.cell(30, 8, f"{invoice['total_ttc']:.2f} EUR", align="R", ln=True)

    pdf.ln(15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0,
        4,
        "Conditions de paiement : virement bancaire sous 30 jours.\n"
        "En cas de retard, une pénalité de 3x le taux d'intérêt légal sera appliquée.\n"
        "Pas d'escompte en cas de paiement anticipé.",
    )

    pdf.output(str(output_path))


def render_invoice_image(invoice, width=1240, height=1754):
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_b_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_b = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_s = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except (OSError, IOError):
        font_b_large = ImageFont.load_default()
        font_b = ImageFont.load_default()
        font = ImageFont.load_default()
        font_s = ImageFont.load_default()

    x_margin = 60
    y = 50

    draw.text((x_margin, y), invoice["emetteur"]["nom"], fill="black", font=font_b_large)
    y += 38
    draw.text((x_margin, y), f"SIREN: {invoice['emetteur']['siren']}  |  SIRET: {invoice['emetteur']['siret']}", fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), invoice["emetteur"]["adresse"], fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), f"Tel: {invoice['emetteur']['telephone']}  |  {invoice['emetteur']['email']}", fill="gray", font=font_s)
    y += 50

    draw.text((width // 2 - 80, y), "FACTURE", fill=(0, 51, 102), font=font_b_large)
    y += 50

    draw.text((x_margin, y), f"N° Facture: {invoice['numero']}", fill="black", font=font_b)
    draw.text((width // 2 + 50, y), f"Date: {invoice['date']}", fill="black", font=font)
    y += 25
    draw.text((x_margin, y), f"Date d'échéance: {invoice['date_echeance']}", fill="black", font=font)
    y += 40

    draw.text((x_margin, y), "Facturer à :", fill="black", font=font_b)
    y += 25
    draw.text((x_margin, y), invoice["client"]["nom"], fill="black", font=font)
    y += 22
    draw.text((x_margin, y), invoice["client"]["adresse"], fill="black", font=font_s)
    y += 20
    draw.text((x_margin, y), invoice["client"]["email"], fill="gray", font=font_s)
    y += 45

    col_x = [x_margin, x_margin + 500, x_margin + 620, x_margin + 780]
    col_headers = ["Description", "Qte", "Prix unit. (EUR)", "Total (EUR)"]
    draw.rectangle([x_margin - 5, y - 3, width - x_margin + 5, y + 25], fill=(0, 51, 102))
    for i, h in enumerate(col_headers):
        draw.text((col_x[i], y), h, fill="white", font=font_b)
    y += 32

    for ligne in invoice["lignes"]:
        draw.text((col_x[0], y), ligne["description"][:45], fill="black", font=font)
        draw.text((col_x[1], y), str(ligne["quantite"]), fill="black", font=font)
        draw.text((col_x[2], y), f"{ligne['prix_unitaire']:.2f}", fill="black", font=font)
        draw.text((col_x[3], y), f"{ligne['total']:.2f}", fill="black", font=font)
        y += 24
        draw.line([(x_margin, y - 2), (width - x_margin, y - 2)], fill=(200, 200, 200))

    y += 30
    tx = width - x_margin - 300
    draw.text((tx, y), "Sous-total HT:", fill="black", font=font)
    draw.text((tx + 200, y), f"{invoice['sous_total']:.2f} EUR", fill="black", font=font)
    y += 25
    draw.text((tx, y), f"TVA ({int(invoice['taux_tva']*100)}%):", fill="black", font=font)
    draw.text((tx + 200, y), f"{invoice['tva']:.2f} EUR", fill="black", font=font)
    y += 28
    draw.line([(tx, y - 3), (width - x_margin, y - 3)], fill="black")
    draw.text((tx, y), "Total TTC:", fill="black", font=font_b)
    draw.text((tx + 200, y), f"{invoice['total_ttc']:.2f} EUR", fill=(0, 51, 102), font=font_b)
    y += 60

    mentions = (
        "Conditions de paiement : virement bancaire sous 30 jours.\n"
        "En cas de retard, une pénalité de 3x le taux d'intérêt légal sera appliquée.\n"
        "Pas d'escompte en cas de paiement anticipé."
    )
    draw.text((x_margin, y), mentions, fill="gray", font=font_s)

    return img


# GENERATION DEVIS
def generate_devis_data(legitimate=True, scenario="normal"):
    emetteur = get_random_company()
    client_name = random_collegue()

    date_devis = fake.date_between(start_date="-30d", end_date="today")
    duree_validite = random.choice([15, 30, 45, 60])
    date_validite = date_devis + timedelta(days=duree_validite)

    nb_lignes = random.randint(1, 5)
    lignes = []
    for _ in range(nb_lignes):
        desc = fake.bs().capitalize()
        qte = random.randint(1, 15)
        prix_unitaire = round(random.uniform(20, 800), 2)
        total_ligne = round(qte * prix_unitaire, 2)
        lignes.append({
            "description": desc,
            "quantite": qte,
            "prix_unitaire": prix_unitaire,
            "total": total_ligne,
        })

    sous_total = round(sum(l["total"] for l in lignes), 2)
    taux_tva = 0.20
    tva = round(sous_total * taux_tva, 2)
    total_ttc = round(sous_total + tva, 2)

    siren = emetteur["siren"]
    siret = generate_siret(siren)

    devis = {
        "doc_type": "devis",
        "numero": f"DEV-{fake.unique.random_int(min=20000, max=39999)}",
        "date": date_devis.strftime("%d/%m/%Y"),
        "date_validite": date_validite.strftime("%d/%m/%Y"),
        "duree_validite_jours": duree_validite,
        "emetteur": {
            "nom": emetteur["denomination"],
            "siren": siren,
            "siret": siret,
            "adresse": fake.address().replace("\n", ", "),
            "telephone": fake.phone_number(),
            "email": fake.company_email(),
        },
        "client": {
            "nom": client_name,
            "adresse": fake.address().replace("\n", ", "),
            "email": fake.email(),
        },
        "lignes": lignes,
        "sous_total": sous_total,
        "taux_tva": taux_tva,
        "tva": tva,
        "total_ttc": total_ttc,
        "conditions": random.choice([
            "Acompte de 30% a la commande, solde a la livraison.",
            "Paiement a reception du devis signe.",
            "50% a la commande, 50% a la livraison.",
        ]),
        "legitimate": True,
        "scenario": "normal",
        "falsifications": [],
    }

    if not legitimate:
        devis["legitimate"] = False
        devis["scenario"] = scenario
        falsifications = []

        if scenario == "siren_mismatch":
            fake_siren = f"{random.randint(100000000, 999999999)}"
            devis["emetteur"]["siren"] = fake_siren
            devis["emetteur"]["siret"] = generate_siret(fake_siren)
            falsifications.append("SIREN ne correspond pas a l'entreprise")

        elif scenario == "date_incoherente":
            date_val_fausse = date_devis - timedelta(days=random.randint(10, 60))
            devis["date_validite"] = date_val_fausse.strftime("%d/%m/%Y")
            falsifications.append("Date de validite anterieure a la date du devis")

        elif scenario == "entreprise_fictive":
            devis["emetteur"]["nom"] = fake.company()
            devis["emetteur"]["siren"] = f"{random.randint(100000000, 999999999)}"
            devis["emetteur"]["siret"] = generate_siret(devis["emetteur"]["siren"])
            falsifications.append("Entreprise fictive avec faux SIREN")

        elif scenario == "expire":
            old_date = fake.date_between(start_date="-10y", end_date="-5y")
            devis["date"] = old_date.strftime("%d/%m/%Y")
            devis["date_validite"] = (old_date + timedelta(days=30)).strftime("%d/%m/%Y")
            falsifications.append("Devis expire (date tres ancienne)")

        devis["falsifications"] = falsifications

    return devis


def render_devis_pdf(devis, output_path):
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, sanitize(devis["emetteur"]["nom"]), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(f"SIREN: {devis['emetteur']['siren']}  |  SIRET: {devis['emetteur']['siret']}"), ln=True)
    pdf.cell(0, 5, sanitize(devis["emetteur"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(f"Tel: {devis['emetteur']['telephone']}  |  {devis['emetteur']['email']}"), ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(34, 120, 15)
    pdf.cell(0, 12, "DEVIS", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 6, f"N. Devis: {devis['numero']}")
    pdf.cell(95, 6, f"Date: {devis['date']}", ln=True)
    pdf.cell(95, 6, f"Valide jusqu'au: {devis['date_validite']}", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Client :", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(devis["client"]["nom"]), ln=True)
    pdf.cell(0, 5, sanitize(devis["client"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(devis["client"]["email"]), ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(34, 120, 15)
    pdf.set_text_color(255, 255, 255)
    col_widths = [80, 25, 35, 40]
    headers = ["Description", "Qte", "Prix unit. (EUR)", "Total (EUR)"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    for ligne in devis["lignes"]:
        pdf.cell(col_widths[0], 7, sanitize(ligne["description"][:40]), border=1)
        pdf.cell(col_widths[1], 7, str(ligne["quantite"]), border=1, align="C")
        pdf.cell(col_widths[2], 7, f"{ligne['prix_unitaire']:.2f}", border=1, align="R")
        pdf.cell(col_widths[3], 7, f"{ligne['total']:.2f}", border=1, align="R")
        pdf.ln()

    pdf.ln(5)
    x_label = 120
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(x_label)
    pdf.cell(45, 7, "Sous-total HT:", align="R")
    pdf.cell(30, 7, f"{devis['sous_total']:.2f} EUR", align="R", ln=True)
    pdf.set_x(x_label)
    pdf.cell(45, 7, f"TVA ({int(devis['taux_tva']*100)}%):", align="R")
    pdf.cell(30, 7, f"{devis['tva']:.2f} EUR", align="R", ln=True)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_x(x_label)
    pdf.cell(45, 8, "Total TTC:", align="R")
    pdf.cell(30, 8, f"{devis['total_ttc']:.2f} EUR", align="R", ln=True)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, sanitize(devis["conditions"]))
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 8)
    pdf.multi_cell(0, 4, "Signature du client precedee de la mention 'Bon pour accord' :\n\n\n__________________________")

    pdf.output(str(output_path))


def render_devis_image(devis, width=1240, height=1754):
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_b_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_b = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_s = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except (OSError, IOError):
        font_b_large = font_b = font = font_s = ImageFont.load_default()

    COLOR = (34, 120, 15)
    x_margin = 60
    y = 50

    draw.text((x_margin, y), devis["emetteur"]["nom"], fill="black", font=font_b_large)
    y += 38
    draw.text((x_margin, y), f"SIREN: {devis['emetteur']['siren']}  |  SIRET: {devis['emetteur']['siret']}", fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), devis["emetteur"]["adresse"], fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), f"Tel: {devis['emetteur']['telephone']}  |  {devis['emetteur']['email']}", fill="gray", font=font_s)
    y += 50

    draw.text((width // 2 - 60, y), "DEVIS", fill=COLOR, font=font_b_large)
    y += 50

    draw.text((x_margin, y), f"N. Devis: {devis['numero']}", fill="black", font=font_b)
    draw.text((width // 2 + 50, y), f"Date: {devis['date']}", fill="black", font=font)
    y += 25
    draw.text((x_margin, y), f"Valide jusqu'au: {devis['date_validite']}", fill="black", font=font)
    y += 40

    draw.text((x_margin, y), "Client :", fill="black", font=font_b)
    y += 25
    draw.text((x_margin, y), devis["client"]["nom"], fill="black", font=font)
    y += 22
    draw.text((x_margin, y), devis["client"]["adresse"], fill="black", font=font_s)
    y += 20
    draw.text((x_margin, y), devis["client"]["email"], fill="gray", font=font_s)
    y += 45

    col_x = [x_margin, x_margin + 500, x_margin + 620, x_margin + 780]
    col_headers = ["Description", "Qte", "Prix unit. (EUR)", "Total (EUR)"]
    draw.rectangle([x_margin - 5, y - 3, width - x_margin + 5, y + 25], fill=COLOR)
    for i, h in enumerate(col_headers):
        draw.text((col_x[i], y), h, fill="white", font=font_b)
    y += 32

    for ligne in devis["lignes"]:
        draw.text((col_x[0], y), ligne["description"][:45], fill="black", font=font)
        draw.text((col_x[1], y), str(ligne["quantite"]), fill="black", font=font)
        draw.text((col_x[2], y), f"{ligne['prix_unitaire']:.2f}", fill="black", font=font)
        draw.text((col_x[3], y), f"{ligne['total']:.2f}", fill="black", font=font)
        y += 24
        draw.line([(x_margin, y - 2), (width - x_margin, y - 2)], fill=(200, 200, 200))

    y += 30
    tx = width - x_margin - 300
    draw.text((tx, y), "Sous-total HT:", fill="black", font=font)
    draw.text((tx + 200, y), f"{devis['sous_total']:.2f} EUR", fill="black", font=font)
    y += 25
    draw.text((tx, y), f"TVA ({int(devis['taux_tva']*100)}%):", fill="black", font=font)
    draw.text((tx + 200, y), f"{devis['tva']:.2f} EUR", fill="black", font=font)
    y += 28
    draw.line([(tx, y - 3), (width - x_margin, y - 3)], fill="black")
    draw.text((tx, y), "Total TTC:", fill="black", font=font_b)
    draw.text((tx + 200, y), f"{devis['total_ttc']:.2f} EUR", fill=COLOR, font=font_b)
    y += 50

    draw.text((x_margin, y), devis["conditions"], fill="gray", font=font_s)
    y += 30
    draw.text((x_margin, y), "Signature du client precedee de 'Bon pour accord' :", fill="gray", font=font_s)
    y += 25
    draw.line([(x_margin, y + 20), (x_margin + 250, y + 20)], fill="black")

    return img


# GENERATION BON DE COMMANDE
def generate_bon_commande_data(legitimate=True, scenario="normal"):
    emetteur = get_random_company()
    fournisseur = get_random_company()

    while fournisseur["siren"] == emetteur["siren"]:
        fournisseur = get_random_company()

    responsable = random_collegue()
    date_commande = fake.date_between(start_date="-45d", end_date="today")
    date_livraison = date_commande + timedelta(days=random.choice([7, 14, 21, 30, 45]))

    nb_lignes = random.randint(1, 6)
    lignes = []
    for _ in range(nb_lignes):
        desc = random.choice([
            "Fournitures de bureau", "Cartouches d'encre", "Papier A4 (ramette x5)",
            "Licences logicielles", "Materiel informatique", "Mobilier de bureau",
            "Prestation de conseil", "Formation professionnelle", "Maintenance serveur",
            "Hebergement cloud", "Cables reseau Cat6", "Ecrans 27 pouces",
        ])
        qte = random.randint(1, 50)
        prix_unitaire = round(random.uniform(5, 1200), 2)
        total_ligne = round(qte * prix_unitaire, 2)
        lignes.append({
            "description": desc,
            "quantite": qte,
            "prix_unitaire": prix_unitaire,
            "total": total_ligne,
        })

    sous_total = round(sum(l["total"] for l in lignes), 2)
    taux_tva = 0.20
    tva = round(sous_total * taux_tva, 2)
    total_ttc = round(sous_total + tva, 2)

    siren_em = emetteur["siren"]
    siret_em = generate_siret(siren_em)
    siren_fr = fournisseur["siren"]
    siret_fr = generate_siret(siren_fr)

    bdc = {
        "doc_type": "bon_commande",
        "numero": f"BDC-{fake.unique.random_int(min=40000, max=59999)}",
        "date": date_commande.strftime("%d/%m/%Y"),
        "date_livraison": date_livraison.strftime("%d/%m/%Y"),
        "emetteur": {
            "nom": emetteur["denomination"],
            "siren": siren_em,
            "siret": siret_em,
            "adresse": fake.address().replace("\n", ", "),
            "telephone": fake.phone_number(),
            "email": fake.company_email(),
        },
        "fournisseur": {
            "nom": fournisseur["denomination"],
            "siren": siren_fr,
            "siret": siret_fr,
            "adresse": fake.address().replace("\n", ", "),
            "telephone": fake.phone_number(),
            "email": fake.company_email(),
        },
        "responsable": responsable,
        "lignes": lignes,
        "sous_total": sous_total,
        "taux_tva": taux_tva,
        "tva": tva,
        "total_ttc": total_ttc,
        "conditions_livraison": random.choice([
            "Livraison sur site sous 15 jours ouvrables.",
            "Livraison franco de port a l'adresse indiquee.",
            "Retrait en entrepot sur rendez-vous.",
        ]),
        "legitimate": True,
        "scenario": "normal",
        "falsifications": [],
    }

    if not legitimate:
        bdc["legitimate"] = False
        bdc["scenario"] = scenario
        falsifications = []

        if scenario == "siren_mismatch":
            fake_siren = f"{random.randint(100000000, 999999999)}"
            bdc["emetteur"]["siren"] = fake_siren
            bdc["emetteur"]["siret"] = generate_siret(fake_siren)
            falsifications.append("SIREN emetteur ne correspond pas")

        elif scenario == "date_incoherente":
            date_liv_fausse = date_commande - timedelta(days=random.randint(10, 60))
            bdc["date_livraison"] = date_liv_fausse.strftime("%d/%m/%Y")
            falsifications.append("Date de livraison anterieure a la date de commande")

        elif scenario == "entreprise_fictive":
            bdc["fournisseur"]["nom"] = fake.company()
            bdc["fournisseur"]["siren"] = f"{random.randint(100000000, 999999999)}"
            bdc["fournisseur"]["siret"] = generate_siret(bdc["fournisseur"]["siren"])
            falsifications.append("Fournisseur fictif avec faux SIREN")

        elif scenario == "expire":
            old_date = fake.date_between(start_date="-10y", end_date="-5y")
            bdc["date"] = old_date.strftime("%d/%m/%Y")
            bdc["date_livraison"] = (old_date + timedelta(days=14)).strftime("%d/%m/%Y")
            falsifications.append("Bon de commande expire (date tres ancienne)")

        bdc["falsifications"] = falsifications

    return bdc


def render_bon_commande_pdf(bdc, output_path):
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, sanitize(bdc["emetteur"]["nom"]), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(f"SIREN: {bdc['emetteur']['siren']}  |  SIRET: {bdc['emetteur']['siret']}"), ln=True)
    pdf.cell(0, 5, sanitize(bdc["emetteur"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(f"Tel: {bdc['emetteur']['telephone']}  |  {bdc['emetteur']['email']}"), ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(180, 90, 0)
    pdf.cell(0, 12, "BON DE COMMANDE", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 6, f"N. BDC: {bdc['numero']}")
    pdf.cell(95, 6, f"Date: {bdc['date']}", ln=True)
    pdf.cell(95, 6, f"Livraison prevue: {bdc['date_livraison']}")
    pdf.cell(95, 6, f"Responsable: {sanitize(bdc['responsable'])}", ln=True)
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Fournisseur :", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(bdc["fournisseur"]["nom"]), ln=True)
    pdf.cell(0, 5, sanitize(f"SIREN: {bdc['fournisseur']['siren']}  |  SIRET: {bdc['fournisseur']['siret']}"), ln=True)
    pdf.cell(0, 5, sanitize(bdc["fournisseur"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(f"Tel: {bdc['fournisseur']['telephone']}  |  {bdc['fournisseur']['email']}"), ln=True)
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(180, 90, 0)
    pdf.set_text_color(255, 255, 255)
    col_widths = [80, 25, 35, 40]
    headers = ["Designation", "Qte", "Prix unit. (EUR)", "Total (EUR)"]
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 10)
    for ligne in bdc["lignes"]:
        pdf.cell(col_widths[0], 7, sanitize(ligne["description"][:40]), border=1)
        pdf.cell(col_widths[1], 7, str(ligne["quantite"]), border=1, align="C")
        pdf.cell(col_widths[2], 7, f"{ligne['prix_unitaire']:.2f}", border=1, align="R")
        pdf.cell(col_widths[3], 7, f"{ligne['total']:.2f}", border=1, align="R")
        pdf.ln()

    pdf.ln(5)
    x_label = 120
    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(x_label)
    pdf.cell(45, 7, "Sous-total HT:", align="R")
    pdf.cell(30, 7, f"{bdc['sous_total']:.2f} EUR", align="R", ln=True)
    pdf.set_x(x_label)
    pdf.cell(45, 7, f"TVA ({int(bdc['taux_tva']*100)}%):", align="R")
    pdf.cell(30, 7, f"{bdc['tva']:.2f} EUR", align="R", ln=True)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_x(x_label)
    pdf.cell(45, 8, "Total TTC:", align="R")
    pdf.cell(30, 8, f"{bdc['total_ttc']:.2f} EUR", align="R", ln=True)

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 9)
    pdf.multi_cell(0, 5, sanitize(bdc["conditions_livraison"]))

    pdf.output(str(output_path))


def render_bon_commande_image(bdc, width=1240, height=1754):
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font_b_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        font_b = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
        font_s = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
    except (OSError, IOError):
        font_b_large = font_b = font = font_s = ImageFont.load_default()

    COLOR = (180, 90, 0)
    x_margin = 60
    y = 50

    draw.text((x_margin, y), bdc["emetteur"]["nom"], fill="black", font=font_b_large)
    y += 38
    draw.text((x_margin, y), f"SIREN: {bdc['emetteur']['siren']}  |  SIRET: {bdc['emetteur']['siret']}", fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), bdc["emetteur"]["adresse"], fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), f"Tel: {bdc['emetteur']['telephone']}  |  {bdc['emetteur']['email']}", fill="gray", font=font_s)
    y += 50

    draw.text((width // 2 - 150, y), "BON DE COMMANDE", fill=COLOR, font=font_b_large)
    y += 50

    draw.text((x_margin, y), f"N. BDC: {bdc['numero']}", fill="black", font=font_b)
    draw.text((width // 2 + 50, y), f"Date: {bdc['date']}", fill="black", font=font)
    y += 25
    draw.text((x_margin, y), f"Livraison prevue: {bdc['date_livraison']}", fill="black", font=font)
    draw.text((width // 2 + 50, y), f"Responsable: {bdc['responsable']}", fill="black", font=font)
    y += 35

    draw.text((x_margin, y), "Fournisseur :", fill="black", font=font_b)
    y += 25
    draw.text((x_margin, y), bdc["fournisseur"]["nom"], fill="black", font=font)
    y += 22
    draw.text((x_margin, y), f"SIREN: {bdc['fournisseur']['siren']}  |  SIRET: {bdc['fournisseur']['siret']}", fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), bdc["fournisseur"]["adresse"], fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), f"Tel: {bdc['fournisseur']['telephone']}  |  {bdc['fournisseur']['email']}", fill="gray", font=font_s)
    y += 40

    col_x = [x_margin, x_margin + 500, x_margin + 620, x_margin + 780]
    col_headers = ["Designation", "Qte", "Prix unit. (EUR)", "Total (EUR)"]
    draw.rectangle([x_margin - 5, y - 3, width - x_margin + 5, y + 25], fill=COLOR)
    for i, h in enumerate(col_headers):
        draw.text((col_x[i], y), h, fill="white", font=font_b)
    y += 32

    for ligne in bdc["lignes"]:
        draw.text((col_x[0], y), ligne["description"][:45], fill="black", font=font)
        draw.text((col_x[1], y), str(ligne["quantite"]), fill="black", font=font)
        draw.text((col_x[2], y), f"{ligne['prix_unitaire']:.2f}", fill="black", font=font)
        draw.text((col_x[3], y), f"{ligne['total']:.2f}", fill="black", font=font)
        y += 24
        draw.line([(x_margin, y - 2), (width - x_margin, y - 2)], fill=(200, 200, 200))

    y += 30
    tx = width - x_margin - 300
    draw.text((tx, y), "Sous-total HT:", fill="black", font=font)
    draw.text((tx + 200, y), f"{bdc['sous_total']:.2f} EUR", fill="black", font=font)
    y += 25
    draw.text((tx, y), f"TVA ({int(bdc['taux_tva']*100)}%):", fill="black", font=font)
    draw.text((tx + 200, y), f"{bdc['tva']:.2f} EUR", fill="black", font=font)
    y += 28
    draw.line([(tx, y - 3), (width - x_margin, y - 3)], fill="black")
    draw.text((tx, y), "Total TTC:", fill="black", font=font_b)
    draw.text((tx + 200, y), f"{bdc['total_ttc']:.2f} EUR", fill=COLOR, font=font_b)
    y += 50

    draw.text((x_margin, y), bdc["conditions_livraison"], fill="gray", font=font_s)

    return img


# EFFETS SCAN
def apply_scan_effects(image, effects=None):
    if effects is None:
        effects = ["rotation", "flou"]

    img = image.copy()

    if "rotation" in effects:
        angle = random.uniform(-3, 3)
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))

    if "flou" in effects:
        radius = random.uniform(0.3, 1.0)
        img = img.filter(ImageFilter.GaussianBlur(radius=radius))

    if "bruit" in effects:
        arr = np.array(img, dtype=np.int16)
        noise = np.random.normal(0, random.randint(8, 25), arr.shape).astype(np.int16)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    if "pixelisation" in effects:
        w, h = img.size
        factor = random.uniform(0.15, 0.35)
        small = img.resize((int(w * factor), int(h * factor)), Image.NEAREST)
        img = small.resize((w, h), Image.NEAREST)

    if "luminosite" in effects:
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(random.uniform(0.6, 0.85))

    if "smartphone" in effects:
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(random.uniform(0.85, 1.15))
        arr = np.array(img, dtype=np.int16)
        noise = np.random.normal(0, 5, arr.shape).astype(np.int16)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)
        angle = random.uniform(-2, 2)
        img = img.rotate(angle, expand=True, fillcolor=(240, 238, 230))

    if "tache" in effects:
        arr = np.array(img)
        cx, cy = random.randint(100, arr.shape[1] - 100), random.randint(100, arr.shape[0] - 100)
        radius = random.randint(20, 60)
        y, x = np.ogrid[: arr.shape[0], : arr.shape[1]]
        mask = ((x - cx) ** 2 + (y - cy) ** 2) < radius**2
        arr[mask] = np.clip(arr[mask].astype(np.int16) - random.randint(30, 80), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    return img


SCAN_SCENARIOS = [
    ["rotation"],
    ["flou"],
    ["bruit"],
    ["pixelisation"],
    ["rotation", "flou"],
    ["rotation", "bruit"],
    ["flou", "bruit"],
    ["smartphone"],
    ["luminosite", "bruit"],
    ["rotation", "flou", "bruit", "tache"],
]


# HELPERS METIER
def create_supplier_base():
    company = get_random_company()
    siren = company["siren"]
    siret = generate_siret(siren)

    return {
        "nom": company["denomination"],
        "siren": siren,
        "siret": siret,
        "adresse": fake.address().replace("\n", ", "),
        "telephone": fake.phone_number(),
        "email": fake.company_email(),
    }


def apply_supplier_to_invoice(invoice, supplier):
    invoice["emetteur"]["nom"] = supplier["nom"]
    invoice["emetteur"]["siren"] = supplier["siren"]
    invoice["emetteur"]["siret"] = supplier["siret"]
    invoice["emetteur"]["adresse"] = supplier["adresse"]
    invoice["emetteur"]["telephone"] = supplier["telephone"]
    invoice["emetteur"]["email"] = supplier["email"]
    return invoice


def apply_supplier_to_devis(devis, supplier):
    devis["emetteur"]["nom"] = supplier["nom"]
    devis["emetteur"]["siren"] = supplier["siren"]
    devis["emetteur"]["siret"] = supplier["siret"]
    devis["emetteur"]["adresse"] = supplier["adresse"]
    devis["emetteur"]["telephone"] = supplier["telephone"]
    devis["emetteur"]["email"] = supplier["email"]
    return devis


def apply_supplier_to_bon_commande(bdc, supplier):
    bdc["fournisseur"]["nom"] = supplier["nom"]
    bdc["fournisseur"]["siren"] = supplier["siren"]
    bdc["fournisseur"]["siret"] = supplier["siret"]
    bdc["fournisseur"]["adresse"] = supplier["adresse"]
    bdc["fournisseur"]["telephone"] = supplier["telephone"]
    bdc["fournisseur"]["email"] = supplier["email"]
    return bdc


def make_same_business_case():
    supplier = create_supplier_base()

    devis = generate_devis_data(legitimate=True, scenario="normal")
    bon_commande = generate_bon_commande_data(legitimate=True, scenario="normal")
    facture = generate_invoice_data(legitimate=True, scenario="normal")

    devis = apply_supplier_to_devis(devis, supplier)
    bon_commande = apply_supplier_to_bon_commande(bon_commande, supplier)
    facture = apply_supplier_to_invoice(facture, supplier)

    contact_name = random_collegue()
    devis["client"]["nom"] = contact_name
    facture["client"]["nom"] = contact_name
    bon_commande["responsable"] = contact_name

    return {
        "supplier": supplier,
        "devis": devis,
        "bon_commande": bon_commande,
        "facture": facture,
    }


# SCENARIOS METIER
def scenario_normal(bundle):
    bundle["devis"]["scenario"] = "normal"
    bundle["bon_commande"]["scenario"] = "normal"
    bundle["facture"]["scenario"] = "normal"

    return {
        "bundle": bundle,
        "expected": {
            "scenario": "normal",
            "expected_status": "conforme",
            "expected_anomalies": []
        }
    }


def scenario_siren_mismatch(bundle):
    fake_siren = f"{random.randint(100000000, 999999999)}"
    fake_siret = generate_siret(fake_siren)

    bundle["devis"]["emetteur"]["siren"] = fake_siren
    bundle["devis"]["emetteur"]["siret"] = fake_siret
    bundle["devis"]["scenario"] = "siren_mismatch"
    bundle["devis"]["legitimate"] = False
    bundle["devis"]["falsifications"] = [
        "SIREN/SIRET du devis incohérent avec les autres documents"
    ]

    bundle["bon_commande"]["scenario"] = "normal"
    bundle["facture"]["scenario"] = "normal"

    return {
        "bundle": bundle,
        "expected": {
            "scenario": "siren_mismatch",
            "expected_status": "non_conforme",
            "expected_anomalies": [
                "SIREN incohérent entre devis, bon_commande et facture"
            ]
        }
    }


def scenario_fake_total(bundle):
    facture = bundle["facture"]

    vrai_ttc = facture["total_ttc"]
    ecart = round(random.uniform(50, 300), 2)
    faux_ttc = round(vrai_ttc + ecart, 2)

    facture["total_ttc"] = faux_ttc
    facture["scenario"] = "fake_total"
    facture["legitimate"] = False
    facture["falsifications"] = [
        "Montant TTC falsifié : HT + TVA ne correspond pas au TTC"
    ]

    bundle["devis"]["scenario"] = "normal"
    bundle["bon_commande"]["scenario"] = "normal"

    return {
        "bundle": bundle,
        "expected": {
            "scenario": "fake_total",
            "expected_status": "non_conforme",
            "expected_anomalies": [
                "Montant TTC incohérent avec HT + TVA"
            ]
        }
    }


SCENARIO_BUILDERS = {
    "normal": scenario_normal,
    "siren_mismatch": scenario_siren_mismatch,
    "fake_total": scenario_fake_total,
}


# RENDU BRUITE
def save_noisy_versions(bundle, noisy_dir: Path):
    noisy_dir.mkdir(parents=True, exist_ok=True)

    devis_img = render_devis_image(bundle["devis"])
    devis_img = apply_scan_effects(devis_img, random.choice(SCAN_SCENARIOS))
    devis_img.save(noisy_dir / "devis_scan.png")

    bdc_img = render_bon_commande_image(bundle["bon_commande"])
    bdc_img = apply_scan_effects(bdc_img, random.choice(SCAN_SCENARIOS))
    bdc_img.save(noisy_dir / "bon_commande_scan.png")

    facture_img = render_invoice_image(bundle["facture"])
    facture_img = apply_scan_effects(facture_img, random.choice(SCAN_SCENARIOS))
    facture_img.save(noisy_dir / "facture_scan.png")


# SAUVEGARDE D'UN CAS
def save_case(case_dir: Path, bundle_result: dict):
    bundle = bundle_result["bundle"]
    expected = bundle_result["expected"]

    clean_dir = case_dir / "clean"
    noisy_dir = case_dir / "noisy"

    clean_dir.mkdir(parents=True, exist_ok=True)
    noisy_dir.mkdir(parents=True, exist_ok=True)

    devis_pdf = clean_dir / "devis.pdf"
    bdc_pdf = clean_dir / "bon_commande.pdf"
    facture_pdf = clean_dir / "facture.pdf"

    render_devis_pdf(bundle["devis"], devis_pdf)
    render_bon_commande_pdf(bundle["bon_commande"], bdc_pdf)
    render_invoice_pdf(bundle["facture"], facture_pdf)

    save_noisy_versions(bundle, noisy_dir)

    payload = {
        "scenario": expected["scenario"],
        "expected_status": expected["expected_status"],
        "expected_anomalies": expected["expected_anomalies"],
        "documents": {
            "devis": {
                "clean_file": "clean/devis.pdf",
                "noisy_file": "noisy/devis_scan.png",
                "numero": bundle["devis"]["numero"],
                "emetteur_nom": bundle["devis"]["emetteur"]["nom"],
                "siren": bundle["devis"]["emetteur"]["siren"],
                "siret": bundle["devis"]["emetteur"]["siret"],
                "total_ttc": bundle["devis"]["total_ttc"],
                "date": bundle["devis"]["date"],
                "falsifications": bundle["devis"].get("falsifications", [])
            },
            "bon_commande": {
                "clean_file": "clean/bon_commande.pdf",
                "noisy_file": "noisy/bon_commande_scan.png",
                "numero": bundle["bon_commande"]["numero"],
                "fournisseur_nom": bundle["bon_commande"]["fournisseur"]["nom"],
                "siren": bundle["bon_commande"]["fournisseur"]["siren"],
                "siret": bundle["bon_commande"]["fournisseur"]["siret"],
                "total_ttc": bundle["bon_commande"]["total_ttc"],
                "date": bundle["bon_commande"]["date"],
                "falsifications": bundle["bon_commande"].get("falsifications", [])
            },
            "facture": {
                "clean_file": "clean/facture.pdf",
                "noisy_file": "noisy/facture_scan.png",
                "numero": bundle["facture"]["numero"],
                "emetteur_nom": bundle["facture"]["emetteur"]["nom"],
                "siren": bundle["facture"]["emetteur"]["siren"],
                "siret": bundle["facture"]["emetteur"]["siret"],
                "sous_total": bundle["facture"]["sous_total"],
                "tva": bundle["facture"]["tva"],
                "total_ttc": bundle["facture"]["total_ttc"],
                "date": bundle["facture"]["date"],
                "falsifications": bundle["facture"].get("falsifications", [])
            }
        }
    }

    with open(case_dir / "expected.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# GENERATION FINALE
def generate_data(output_dir="data/raw"):
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    scenarios = [
        ("scenario_01_normal", "normal"),
        ("scenario_02_siren_mismatch", "siren_mismatch"),
        ("scenario_03_fake_total", "fake_total"),
    ]

    manifest = []

    for folder_name, scenario_name in scenarios:
        bundle = make_same_business_case()
        builder = SCENARIO_BUILDERS[scenario_name]
        result = builder(bundle)

        case_dir = base / folder_name
        save_case(case_dir, result)

        manifest.append({
            "folder": folder_name,
            "scenario": scenario_name,
            "expected_status": result["expected"]["expected_status"],
            "expected_anomalies": result["expected"]["expected_anomalies"],
            "clean_documents_count": 3,
            "noisy_documents_count": 3
        })

        print(f"[OK] {folder_name} généré")

    with open(base / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\nData métier généré avec succès")
    print(f"Dossier: {base}")


# MAIN
if __name__ == "__main__":
    load_siren_data(n=200)
    generate_data(output_dir="../data/raw")

    print("\nData métier généré avec succès !")
    print("Structure:")
    print("  data/")
    print("    raw/")
    print("      scenario_01_normal/")
    print("        clean/  noisy/  expected.json")
    print("      scenario_02_siren_mismatch/")
    print("        clean/  noisy/  expected.json")
    print("      scenario_03_fake_total/")
    print("        clean/  noisy/  expected.json")
    print("      manifest.json")