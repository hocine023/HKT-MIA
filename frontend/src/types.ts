export type DocumentStatus =
  | "conforme"
  | "à vérifier"
  | "a_verifier"
  | "non_conforme";

export interface LineItem {
  description?: string | null;
  quantite?: number | null;
  prix_unitaire?: number | null;
  total?: number | null;
}

export interface ExtractedFields {
  numero?: string | null;
  emetteur?: string | null;
  fournisseur?: string | null;
  siren?: string | null;
  siret?: string | null;
  client?: string | null;

  total_ttc?: number | null;
  sous_total_ht?: number | null;
  tva_taux?: number | null;
  tva_montant?: number | null;

  date?: string | null;
  adresse?: string | null;
  code_postal?: string | null;
  ville?: string | null;
  dates_trouvees?: string[];

  lignes?: LineItem[] | null;
}

export interface DocumentData {
  document_id: string;
  document_type: string;
  extracted_fields: ExtractedFields;

  source_clean_file?: string;
  source_raw_file?: string;
  ocr_engine?: string;
  document_type_hint?: string;
  batch_id?: string;
}

export interface ValidationCheck {
  rule?: string;
  status?: "passed" | "failed" | "not_applicable" | string;
  message?: string;
}

export interface ValidationResult {
  global_status?: DocumentStatus;
  status?: DocumentStatus;
  anomalies?: string[];
  checks?: ValidationCheck[];
  confidence?: number | null;
}

export interface ProcessingResult {
  batch_id: string;
  documents: DocumentData[];
  validation: ValidationResult | null;
}