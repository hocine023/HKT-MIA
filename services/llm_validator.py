import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN manquant dans .env")

HF_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:cheapest"


def build_validation_prompt(bundle: dict) -> str:
    return f"""
Tu es un moteur de validation documentaire comptable.

Tu reçois des documents structurés issus de :
- devis
- bon_commande
- facture

Tu dois :
1. vérifier la cohérence inter-documents
2. vérifier la cohérence interne de la facture
3. retourner UNIQUEMENT un JSON valide
4. ne jamais inventer une donnée absente
5. ne pas utiliser le champ "emetteur" pour les règles de validation

Règles à vérifier :
- présence des documents attendus
- présence des champs minimums utiles
- cohérence du siren entre devis et facture et fournisseur BDC
- cohérence du siret entre devis et facture et fournisseur BDC
- cohérence du client entre devis et facture et fournisseur BDC
- pour la facture : sous_total_ht + tva_montant = total_ttc
- pour la facture : somme des lignes = sous_total_ht
- pour la facture : tva_montant cohérent avec tva_taux

Voici les données :
{json.dumps(bundle, ensure_ascii=False, indent=2)}

Retourne exactement ce JSON :
{{
  "global_status": "conforme | a_verifier | non_conforme",
  "checks": [
    {{
      "rule": "",
      "status": "passed | failed | not_applicable",
      "message": ""
    }}
  ],
  "anomalies": [],
  "confidence": 0.0
}}
""".strip()


def call_hf_chat(prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Tu réponds uniquement en JSON valide."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    response = requests.post(HF_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def validate_bundle_with_llm(bundle: dict) -> dict:
    prompt = build_validation_prompt(bundle)
    return call_hf_chat(prompt)