import { useStore } from '../store';
import { useNavigate } from 'react-router-dom';
import { FileUp, Loader2 } from 'lucide-react';

export const UploadPage = () => {
  const { setBatch, isLoading, setLoading } = useStore();
  const navigate = useNavigate();

  const handleProcess = () => {
    setLoading(true);
    
    // MOCK : Simulation du temps de traitement de l'IA (2 secondes)
    setTimeout(() => {
      setBatch({
        batch_id: "batch_001",
        documents: [
          {
            document_id: "doc_01",
            filename: "facture_fournisseur.pdf",
            document_type: "facture",
            extracted_fields: {
              company_name: "ABC SARL",
              siret: "12345678900012",
              montant_ttc: 1200.0,
            }
          }
        ],
        validation: {
          status: "non_conforme",
          anomalies: [
            "SIRET incohérent entre facture et attestation",
            "Attestation expirée"
          ]
        }
      });
      setLoading(false);
      navigate('/crm'); // Redirection auto vers le CRM simulé
    }, 2000);
  };

  return (
    <div className="p-8 max-w-2xl mx-auto text-center animate-in fade-in duration-500">
      <h1 className="text-3xl font-bold mb-8 text-slate-800">1. Ingestion & Traitement IA</h1>
      
      <div className="border-4 border-dashed border-slate-300 hover:border-blue-500 transition-colors p-16 rounded-2xl mb-8 bg-white cursor-pointer group flex flex-col items-center gap-4">
        <FileUp size={64} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
        <p className="text-xl text-slate-600 font-medium">Glissez vos documents comptables ici</p>
        <p className="text-sm text-slate-400">(PDF, PNG, JPG)</p>
      </div>

      <button 
        onClick={handleProcess}
        disabled={isLoading}
        className="px-8 py-4 bg-blue-600 text-white font-bold rounded-xl shadow-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-3 mx-auto transition-all"
      >
        {isLoading ? <Loader2 className="animate-spin" /> : "Lancer l'Extraction OCR & Validation"}
      </button>
    </div>
  );
};