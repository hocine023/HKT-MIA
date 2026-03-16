import { useStore } from '../store';
import { Database } from 'lucide-react';

export const CRMPage = () => {
  const { currentBatch } = useStore();
  const doc = currentBatch?.documents[0]; // On prend le premier doc pour la démo

  return (
    <div className="p-8 max-w-4xl mx-auto animate-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-8 border-b pb-4">
        <Database className="text-blue-600" size={32} />
        <h1 className="text-2xl font-bold text-slate-800">2. CRM - Fiche Fournisseur</h1>
        <span className="ml-auto px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold uppercase tracking-wide">Auto-rempli par IA</span>
      </div>
      
      {!doc ? (
        <p className="text-slate-500 bg-slate-50 p-6 rounded-lg border text-center">Aucune donnée disponible. Lancez un traitement d'abord.</p>
      ) : (
        <div className="grid grid-cols-2 gap-8 bg-white p-8 rounded-xl shadow-sm border border-slate-200">
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Raison Sociale</label>
            <p className="text-xl font-semibold text-slate-900">{doc.extracted_fields.company_name || '-'}</p>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">N° SIRET</label>
            <p className="text-xl font-mono text-slate-900">{doc.extracted_fields.siret || '-'}</p>
          </div>
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Montant Facture (TTC)</label>
            <p className="text-xl font-semibold text-slate-900">{doc.extracted_fields.montant_ttc ? `${doc.extracted_fields.montant_ttc} €` : '-'}</p>
          </div>
        </div>
      )}
    </div>
  );
};