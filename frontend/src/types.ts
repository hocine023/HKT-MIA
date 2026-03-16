export type DocumentStatus = 'conforme' | 'à vérifier' | 'non_conforme';

export interface ExtractedFields {
  company_name?: string;
  siret?: string;
  tva?: string;
  date_emission?: string;
  date_expiration?: string | null;
  montant_ht?: number;
  montant_ttc?: number;
  iban?: string | null;
}

export interface DocumentData {
  document_id: string;
  filename: string;
  document_type: string;
  ocr_text?: string;
  extracted_fields: ExtractedFields;
}

export interface ProcessingResult {
  batch_id: string;
  documents: DocumentData[];
  validation: {
    status: DocumentStatus;
    anomalies: string[];
  };
}