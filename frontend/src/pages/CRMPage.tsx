import { useStore } from '../store';
import { Database } from 'lucide-react';

export const CRMPage = () => {
  const { currentBatch } = useStore();
  const docs = currentBatch?.documents ?? [];

  return (
    <div className="p-8 max-w-4xl mx-auto animate-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-8 border-b pb-4">
        <Database className="text-blue-600" size={32} />
        <h1 className="text-2xl font-bold text-slate-800">2. CRM - Fiches Fournisseurs</h1>
        <span className="ml-auto px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold uppercase tracking-wide">Auto-rempli par IA</span>
      </div>
      
      {docs.length === 0 ? (
        <p className="text-slate-500 bg-slate-50 p-6 rounded-lg border text-center">Aucune donnée disponible. Lancez un traitement d'abord.</p>
      ) : (
        <div className="space-y-6">
          {docs.map((doc) => (
            <div key={doc.document_id} className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
              <h3 className="text-sm font-bold text-blue-600 uppercase tracking-wider mb-4">
                {doc.document_type} — {doc.document_id}
              </h3>
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Raison Sociale</label>
                  <p className="text-lg font-semibold text-slate-900">{doc.extracted_fields.company_name || '-'}</p>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">N° SIRET</label>
                  <p className="text-lg font-mono text-slate-900">{doc.extracted_fields.siret || '-'}</p>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Montant HT</label>
                  <p className="text-lg font-semibold text-slate-900">{doc.extracted_fields.montant_ht ? `${doc.extracted_fields.montant_ht} €` : '-'}</p>
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Montant TTC</label>
                  <p className="text-lg font-semibold text-slate-900">{doc.extracted_fields.montant_ttc ? `${doc.extracted_fields.montant_ttc} €` : '-'}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};