
import csv
import random
import os
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

from faker import Faker
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

fake = Faker("fr_FR")
random.seed(42)
Faker.seed(42)


# Noms des collègues du hackathon
COLLEGUES = [
    {"prenom": "Hocine", "nom": "AKLI"},
    {"prenom": "Anass", "nom": "HOUDZI"},
    {"prenom": "Samy", "nom": "CHEMOUNE"},
    {"prenom": "Erwann", "nom": "HILLION"},
    {"prenom": "Souhir", "nom": "BEJI"},
    {"prenom": "Haithem", "nom": "HENOUDA"},
    {"prenom": "Erwan", "nom": "MARCHAND"},
]

# Chargement de vraies entreprises SIREN
SIREN_CSV = Path(__file__).parent / "StockUniteLegale_utf8.csv"
REAL_COMPANIES = []

# Permet de load les datas des sirens
def load_siren_data(n=200):
    global REAL_COMPANIES
    print(f"Chargement de {n} entreprises depuis {SIREN_CSV}...")
    count = 0
    with open(SIREN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # On filtre pour n'avoir que des entreprises actives (etatAdministratifUniteLegale = "A") avec un nom et un SIREN valide
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
                        "categorie_juridique": row.get(
                            "categorieJuridiqueUniteLegale", ""
                        ),
                        "activite": row.get(
                            "activitePrincipaleUniteLegale", ""
                        ),
                    }
                )
                count += 1
                if count >= n:
                    break
    print(f"  -> {len(REAL_COMPANIES)} entreprises chargées.")


def get_random_company():
    return random.choice(REAL_COMPANIES)


# Génération d'un SIRET à partir d'un SIREN (en ajoutant un NIC aléatoire)
def generate_siret(siren):
    nic = f"{random.randint(1, 99999):05d}"
    return f"{siren}{nic}"


def random_collegue():
    c = random.choice(COLLEGUES)
    return f"{c['prenom']} {c['nom']}"


# Génération de factures PDF
class InvoicePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def generate_invoice_data(legitimate=True, scenario="normal"):

    emetteur = get_random_company()
    client_name = random_collegue()

    date_facture = fake.date_between(start_date="-2y", end_date="today")
    date_echeance = date_facture + timedelta(days=random.choice([30, 45, 60, 90]))

    # Lignes de facture
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

    # ── Appliquer les falsifications ──
    if not legitimate:
        invoice["legitimate"] = False
        invoice["scenario"] = scenario
        falsifications = []

        if scenario == "siren_mismatch":
            # SIREN qui ne correspond pas
            fake_siren = f"{random.randint(100000000, 999999999)}"
            invoice["emetteur"]["siren"] = fake_siren
            invoice["emetteur"]["siret"] = generate_siret(fake_siren)
            falsifications.append("SIREN ne correspond pas à l'entreprise")

        elif scenario == "montant_aberrant":
            # Total ne correspond pas à la somme des lignes
            invoice["total_ttc"] = round(total_ttc * random.uniform(1.3, 2.5), 2)
            falsifications.append("Total TTC incohérent avec les lignes")

        elif scenario == "date_incoherente":
            # Date d'échéance AVANT la date de facture
            date_ech_fausse = date_facture - timedelta(days=random.randint(10, 90))
            invoice["date_echeance"] = date_ech_fausse.strftime("%d/%m/%Y")
            falsifications.append("Date d'échéance antérieure à la date de facture")

        elif scenario == "tva_fausse":
            # TVA mal calculée
            invoice["tva"] = round(tva * random.uniform(0.3, 0.7), 2)
            invoice["total_ttc"] = round(
                sous_total + invoice["tva"], 2
            )
            falsifications.append("TVA incorrectement calculée")

        elif scenario == "entreprise_fictive":
            # Entreprise complètement inventée
            invoice["emetteur"]["nom"] = fake.company()
            invoice["emetteur"]["siren"] = f"{random.randint(100000000, 999999999)}"
            invoice["emetteur"]["siret"] = generate_siret(
                invoice["emetteur"]["siren"]
            )
            falsifications.append("Entreprise fictive avec faux SIREN")

        elif scenario == "expire":
            # Facture très ancienne
            old_date = fake.date_between(start_date="-10y", end_date="-5y")
            invoice["date"] = old_date.strftime("%d/%m/%Y")
            invoice["date_echeance"] = (old_date + timedelta(days=30)).strftime(
                "%d/%m/%Y"
            )
            falsifications.append("Document expiré (date très ancienne)")

        invoice["falsifications"] = falsifications

    return invoice


# FPDF a du mal avec certains caractères spéciaux, on va faire un encodage simple pour éviter les erreurs d'affichage
def sanitize(text):
    return text.encode("latin-1", errors="replace").decode("latin-1")


# Render PDF à partir des données de la facture
def render_invoice_pdf(invoice, output_path):
    pdf = InvoicePDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ── En-tête entreprise ──
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, sanitize(invoice["emetteur"]["nom"]), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(f"SIREN: {invoice['emetteur']['siren']}  |  SIRET: {invoice['emetteur']['siret']}"), ln=True)
    pdf.cell(0, 5, sanitize(invoice["emetteur"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(f"Tel: {invoice['emetteur']['telephone']}  |  {invoice['emetteur']['email']}"), ln=True)
    pdf.ln(10)

    # ── Titre FACTURE ──
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 12, "FACTURE", ln=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # ── Infos facture ──
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 6, f"N\u00b0 Facture: {invoice['numero']}")
    pdf.cell(95, 6, f"Date: {invoice['date']}", ln=True)
    pdf.cell(95, 6, f"Date d'\u00e9ch\u00e9ance: {invoice['date_echeance']}", ln=True)
    pdf.ln(5)

    # ── Client ──
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Facturer \u00e0 :", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, sanitize(invoice["client"]["nom"]), ln=True)
    pdf.cell(0, 5, sanitize(invoice["client"]["adresse"]), ln=True)
    pdf.cell(0, 5, sanitize(invoice["client"]["email"]), ln=True)
    pdf.ln(10)

    # ── Tableau des lignes ──
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

    # ── Totaux ──
    x_label = 120
    x_val = 165
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

    # ── Mentions légales ──
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(
        0,
        4,
        "Conditions de paiement : virement bancaire sous 30 jours.\n"
        "En cas de retard, une p\u00e9nalit\u00e9 de 3x le taux d'int\u00e9r\u00eat l\u00e9gal sera appliqu\u00e9e.\n"
        "Pas d'escompte en cas de paiement anticip\u00e9.",
    )

    pdf.output(str(output_path))



# DEVIS
def generate_devis_data(legitimate=True, scenario="normal"):
    emetteur = get_random_company()
    client_name = random_collegue()

    date_devis = fake.date_between(start_date="-2y", end_date="today")
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

        elif scenario == "montant_aberrant":
            devis["total_ttc"] = round(total_ttc * random.uniform(1.3, 2.5), 2)
            falsifications.append("Total TTC incoherent avec les lignes")

        elif scenario == "date_incoherente":
            date_val_fausse = date_devis - timedelta(days=random.randint(10, 60))
            devis["date_validite"] = date_val_fausse.strftime("%d/%m/%Y")
            falsifications.append("Date de validite anterieure a la date du devis")

        elif scenario == "tva_fausse":
            devis["tva"] = round(tva * random.uniform(0.3, 0.7), 2)
            devis["total_ttc"] = round(sous_total + devis["tva"], 2)
            falsifications.append("TVA incorrectement calculee")

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


# BON DE COMMANDE
def generate_bon_commande_data(legitimate=True, scenario="normal"):
    emetteur = get_random_company()
    fournisseur = get_random_company()
    # S'assurer que emetteur != fournisseur
    while fournisseur["siren"] == emetteur["siren"]:
        fournisseur = get_random_company()

    responsable = random_collegue()
    date_commande = fake.date_between(start_date="-2y", end_date="today")
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

        elif scenario == "montant_aberrant":
            bdc["total_ttc"] = round(total_ttc * random.uniform(1.3, 2.5), 2)
            falsifications.append("Total TTC incoherent avec les lignes")

        elif scenario == "date_incoherente":
            date_liv_fausse = date_commande - timedelta(days=random.randint(10, 60))
            bdc["date_livraison"] = date_liv_fausse.strftime("%d/%m/%Y")
            falsifications.append("Date de livraison anterieure a la date de commande")

        elif scenario == "tva_fausse":
            bdc["tva"] = round(tva * random.uniform(0.3, 0.7), 2)
            bdc["total_ttc"] = round(sous_total + bdc["tva"], 2)
            falsifications.append("TVA incorrectement calculee")

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

    # Fournisseur
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

    # Fournisseur
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



# Effets "scan" pour simuler des documents numérisés
def render_invoice_image(invoice, width=1240, height=1754):
    """Rend la facture directement en image (A4 ~150dpi) avec Pillow."""
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # Fonts (utilise les fonts par défaut de Pillow)
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

    # En-tête entreprise
    draw.text((x_margin, y), invoice["emetteur"]["nom"], fill="black", font=font_b_large)
    y += 38
    draw.text((x_margin, y), f"SIREN: {invoice['emetteur']['siren']}  |  SIRET: {invoice['emetteur']['siret']}", fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), invoice["emetteur"]["adresse"], fill="gray", font=font_s)
    y += 20
    draw.text((x_margin, y), f"Tel: {invoice['emetteur']['telephone']}  |  {invoice['emetteur']['email']}", fill="gray", font=font_s)
    y += 50

    # Titre FACTURE
    draw.text((width // 2 - 80, y), "FACTURE", fill=(0, 51, 102), font=font_b_large)
    y += 50

    # Infos facture
    draw.text((x_margin, y), f"N\u00b0 Facture: {invoice['numero']}", fill="black", font=font_b)
    draw.text((width // 2 + 50, y), f"Date: {invoice['date']}", fill="black", font=font)
    y += 25
    draw.text((x_margin, y), f"Date d'\u00e9ch\u00e9ance: {invoice['date_echeance']}", fill="black", font=font)
    y += 40

    # Client
    draw.text((x_margin, y), "Facturer \u00e0 :", fill="black", font=font_b)
    y += 25
    draw.text((x_margin, y), invoice["client"]["nom"], fill="black", font=font)
    y += 22
    draw.text((x_margin, y), invoice["client"]["adresse"], fill="black", font=font_s)
    y += 20
    draw.text((x_margin, y), invoice["client"]["email"], fill="gray", font=font_s)
    y += 45

    # Tableau - en-tête
    col_x = [x_margin, x_margin + 500, x_margin + 620, x_margin + 780]
    col_headers = ["Description", "Qte", "Prix unit. (EUR)", "Total (EUR)"]
    draw.rectangle([x_margin - 5, y - 3, width - x_margin + 5, y + 25], fill=(0, 51, 102))
    for i, h in enumerate(col_headers):
        draw.text((col_x[i], y), h, fill="white", font=font_b)
    y += 32

    # Tableau - lignes
    for ligne in invoice["lignes"]:
        draw.text((col_x[0], y), ligne["description"][:45], fill="black", font=font)
        draw.text((col_x[1], y), str(ligne["quantite"]), fill="black", font=font)
        draw.text((col_x[2], y), f"{ligne['prix_unitaire']:.2f}", fill="black", font=font)
        draw.text((col_x[3], y), f"{ligne['total']:.2f}", fill="black", font=font)
        y += 24
        # Ligne de séparation
        draw.line([(x_margin, y - 2), (width - x_margin, y - 2)], fill=(200, 200, 200))

    y += 30

    # Totaux
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

    # Mentions légales
    mentions = (
        "Conditions de paiement : virement bancaire sous 30 jours.\n"
        "En cas de retard, une p\u00e9nalit\u00e9 de 3x le taux d'int\u00e9r\u00eat l\u00e9gal sera appliqu\u00e9e.\n"
        "Pas d'escompte en cas de paiement anticip\u00e9."
    )
    draw.text((x_margin, y), mentions, fill="gray", font=font_s)

    return img

# Appliquer des effets pour simuler un scan (rotation, flou, bruit, etc.)
def apply_scan_effects(image, effects=None):
    if effects is None:
        effects = ["rotation", "flou"]

    img = image.copy()

    if "rotation" in effects:
        angle = random.uniform(-3, 3)
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))

    if "flou" in effects:
        radius = random.uniform(0.5, 2.0)
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
        # Simule une photo prise au smartphone: léger flou + perspective + bruit léger
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
        # Simule une tache/marque sur le scan
        arr = np.array(img)
        cx, cy = random.randint(100, arr.shape[1] - 100), random.randint(100, arr.shape[0] - 100)
        radius = random.randint(20, 60)
        y, x = np.ogrid[: arr.shape[0], : arr.shape[1]]
        mask = ((x - cx) ** 2 + (y - cy) ** 2) < radius**2
        arr[mask] = np.clip(arr[mask].astype(np.int16) - random.randint(30, 80), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    return img


# Génération du dataset complet
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

FRAUD_SCENARIOS = [
    "siren_mismatch",
    "montant_aberrant",
    "date_incoherente",
    "tva_fausse",
    "entreprise_fictive",
    "expire",
]


DOC_TYPES = {
    "facture": {
        "generate": generate_invoice_data,
        "render_pdf": render_invoice_pdf,
        "render_image": render_invoice_image,
        "prefix": "fac",
    },
    "devis": {
        "generate": generate_devis_data,
        "render_pdf": render_devis_pdf,
        "render_image": render_devis_image,
        "prefix": "dev",
    },
    "bon_commande": {
        "generate": generate_bon_commande_data,
        "render_pdf": render_bon_commande_pdf,
        "render_image": render_bon_commande_image,
        "prefix": "bdc",
    },
}


def generate_dataset(
    output_dir="dataset",
    n_per_type=None,
):
    """
    n_per_type: dict par type de doc, ex:
    {"facture": {"legit_pdf": 20, "legit_scan": 20, "fraud_pdf": 15, "fraud_scan": 15}, ...}
    """
    if n_per_type is None:
        n_per_type = {
            "facture":      {"legit_pdf": 20, "legit_scan": 20, "fraud_pdf": 15, "fraud_scan": 15},
            "devis":        {"legit_pdf": 15, "legit_scan": 15, "fraud_pdf": 10, "fraud_scan": 10},
            "bon_commande": {"legit_pdf": 15, "legit_scan": 15, "fraud_pdf": 10, "fraud_scan": 10},
        }

    base = Path(output_dir)

    # Creer la structure de dossiers
    for doc_type in n_per_type:
        for split in ["train", "test"]:
            for cat in ["legitimate", "fraudulent"]:
                for fmt in ["pdf", "scan"]:
                    (base / doc_type / split / cat / fmt).mkdir(parents=True, exist_ok=True)

    metadata = []

    def gen_batch(doc_type, n, legitimate, is_scan, split):
        dt = DOC_TYPES[doc_type]
        for i in range(n):
            scenario = "normal" if legitimate else random.choice(FRAUD_SCENARIOS)
            doc = dt["generate"](legitimate=legitimate, scenario=scenario)

            cat = "legitimate" if legitimate else "fraudulent"
            fmt = "scan" if is_scan else "pdf"
            prefix_leg = "leg" if legitimate else "frd"
            fname = f"{dt['prefix']}_{prefix_leg}_{fmt}_{split}_{i:04d}"

            pdf_path = base / doc_type / split / cat / fmt / f"{fname}.pdf"
            dt["render_pdf"](doc, pdf_path)

            if is_scan:
                effects = random.choice(SCAN_SCENARIOS)
                img = dt["render_image"](doc)
                img = apply_scan_effects(img, effects)
                scan_path = base / doc_type / split / cat / fmt / f"{fname}.png"
                img.save(str(scan_path), "PNG")
                doc["scan_effects"] = effects
                doc["file_scan"] = str(scan_path)

            doc["file_pdf"] = str(pdf_path)
            doc["split"] = split
            doc["format"] = fmt

            # Metadata
            emetteur = doc.get("emetteur", {})
            client = doc.get("client", {}).get("nom", doc.get("responsable", ""))
            meta_entry = {
                "doc_type": doc_type,
                "file": str(pdf_path),
                "file_scan": doc.get("file_scan", ""),
                "split": split,
                "format": fmt,
                "legitimate": doc["legitimate"],
                "scenario": doc["scenario"],
                "falsifications": doc.get("falsifications", []),
                "scan_effects": doc.get("scan_effects", []),
                "numero": doc["numero"],
                "emetteur": emetteur.get("nom", ""),
                "siren": emetteur.get("siren", ""),
                "client": client,
                "total_ttc": doc.get("total_ttc", 0),
                "date": doc["date"],
            }
            metadata.append(meta_entry)

            if (i + 1) % 10 == 0:
                print(f"  [{doc_type}/{split}/{cat}/{fmt}] {i+1}/{n}")

    print("\n=== Generation du dataset ===\n")

    for doc_type, counts in n_per_type.items():
        for key, is_legit, is_scan in [
            ("legit_pdf", True, False),
            ("legit_scan", True, True),
            ("fraud_pdf", False, False),
            ("fraud_scan", False, True),
        ]:
            n_total = counts[key]
            n_train = int(n_total * 0.7)
            n_test = n_total - n_train

            label = "legitimes" if is_legit else "frauduleux"
            fmt_label = "SCAN" if is_scan else "PDF"
            print(f">> {doc_type} {label} {fmt_label} (train={n_train}, test={n_test})...")
            gen_batch(doc_type, n_train, legitimate=is_legit, is_scan=is_scan, split="train")
            gen_batch(doc_type, n_test, legitimate=is_legit, is_scan=is_scan, split="test")

    # Sauvegarder les metadonnees
    meta_path = base / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"\nMetadata sauvee: {meta_path}")

    # Stats
    from collections import Counter
    total = len(metadata)
    legit = sum(1 for m in metadata if m["legitimate"])
    fraud = total - legit
    print(f"\n=== STATS ===")
    print(f"Total documents: {total}")
    print(f"  Legitimes: {legit}")
    print(f"  Frauduleux: {fraud}")
    print(f"  Train: {sum(1 for m in metadata if m['split'] == 'train')}")
    print(f"  Test: {sum(1 for m in metadata if m['split'] == 'test')}")

    doc_counts = Counter(m["doc_type"] for m in metadata)
    print(f"\nPar type de document:")
    for dt, cnt in doc_counts.most_common():
        print(f"  {dt}: {cnt}")

    fraud_counts = Counter(m["scenario"] for m in metadata if not m["legitimate"])
    print(f"\nScenarios de fraude:")
    for sc, cnt in fraud_counts.most_common():
        print(f"  {sc}: {cnt}")

    return metadata


# MAIN
if __name__ == "__main__":
    load_siren_data(n=200)

    generate_dataset(
        output_dir="dataset",
        n_per_type={
            "facture":      {"legit_pdf": 50, "legit_scan": 50, "fraud_pdf": 35, "fraud_scan": 35},
            "devis":        {"legit_pdf": 50, "legit_scan": 50, "fraud_pdf": 35, "fraud_scan": 35},
            "bon_commande": {"legit_pdf": 50, "legit_scan": 50, "fraud_pdf": 35, "fraud_scan": 35},
        },
    )

    print("\n Dataset genere avec succes !")
    print("Structure:")
    print("  dataset/")
    print("    facture/     devis/     bon_commande/")
    print("      train/  test/")
    print("        legitimate/  fraudulent/")
    print("          pdf/  scan/")
    print("    metadata.json")
