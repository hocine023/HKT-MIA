import { useStore } from '../store';
import { ShieldAlert, AlertTriangle, CheckCircle2 } from 'lucide-react';

export const CompliancePage = () => {
  const { currentBatch } = useStore();
  
  if (!currentBatch) {
    return <div className="p-8 text-center text-slate-500">Aucune donnée de conformité disponible.</div>;
  }

  const { status, anomalies } = currentBatch.validation;
  const isConforme = status === 'conforme';

  return (
    <div className="p-8 max-w-4xl mx-auto animate-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-8 border-b pb-4">
        <ShieldAlert className={isConforme ? "text-green-600" : "text-red-600"} size={32} />
        <h1 className="text-2xl font-bold text-slate-800">3. Outil de Conformité</h1>
      </div>

      <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
        <div className="flex items-center gap-4 mb-8">
          <span className="text-lg font-semibold text-slate-600">Statut global :</span>
          <span className={`px-4 py-2 rounded-full text-sm font-bold uppercase tracking-wider flex items-center gap-2 ${isConforme ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {isConforme ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            {status.replace('_', ' ')}
          </span>
        </div>

        {anomalies.length > 0 && (
          <div className="space-y-4">
            <h3 className="font-bold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="text-amber-500" size={20} />
              Incohérences inter-documents détectées ({anomalies.length})
            </h3>
            <ul className="space-y-3">
              {anomalies.map((anomalie, idx) => (
                <li key={idx} className="p-4 bg-red-50 text-red-800 rounded-lg border border-red-100 flex items-start gap-3 font-medium">
                  <span className="mt-1 h-2 w-2 bg-red-500 rounded-full flex-shrink-0" />
                  {anomalie}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};