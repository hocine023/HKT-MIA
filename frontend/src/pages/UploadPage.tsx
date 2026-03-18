import { useStore } from '../store';
import { useNavigate } from 'react-router-dom';
import { FileUp, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { triggerDag, getDagRunStatus, fetchAllResults } from '../api';
import { useRef, useState, useCallback } from 'react';

const POLL_INTERVAL_MS = 3000;

export const UploadPage = () => {
  const { setBatch, isLoading, setLoading, dagState, setDagRun, error, setError } = useStore();
  const navigate = useNavigate();
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const onFilesSelected = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;
    setSelectedFiles(Array.from(files));
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    onFilesSelected(e.dataTransfer.files);
  }, [onFilesSelected]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const handleProcess = async () => {
    setLoading(true);
    setError(null);

    try {
      const run = await triggerDag();
      setDagRun(run.dag_run_id, run.state);

      // Poll until DAG finishes
      pollingRef.current = setInterval(async () => {
        try {
          const status = await getDagRunStatus(run.dag_run_id);
          setDagRun(status.dag_run_id, status.state);

          if (status.state === 'success') {
            stopPolling();
            // Fetch results from MongoDB via Airflow plugin
            const data = await fetchAllResults();

            // Map to ProcessingResult
            const docs = data.documents
              .filter((d: Record<string, unknown>) => (d as { _type?: string })._type !== 'validation')
              .map((d: Record<string, unknown>) => {
                const ef = (d.extracted_fields ?? {}) as Record<string, unknown>;
                return {
                  document_id: String(d.document_id ?? ''),
                  filename: String(d.source_raw_file ?? d.document_id ?? ''),
                  document_type: String(d.document_type ?? ''),
                  extracted_fields: {
                    company_name: (ef.emetteur ?? ef.fournisseur) as string | undefined,
                    siret: ef.siret as string | undefined,
                    montant_ht: ef.sous_total_ht as number | undefined,
                    montant_ttc: ef.total_ttc as number | undefined,
                  },
                };
              });

            const validation = data.validations[0] as Record<string, unknown> | undefined;
            const anomalies: string[] = [];
            if (validation?.anomalies && Array.isArray(validation.anomalies)) {
              for (const a of validation.anomalies as Array<Record<string, unknown>>) {
                anomalies.push(String(a.description ?? a));
              }
            }

            const globalStatus = String(validation?.global_status ?? '');
            const status = globalStatus === 'conforme' ? 'conforme'
              : globalStatus === 'non_conforme' ? 'non_conforme'
              : 'à vérifier';

            setBatch({
              batch_id: run.dag_run_id,
              documents: docs,
              validation: {
                status,
                anomalies,
              },
            });

            setLoading(false);
            navigate('/crm');
          } else if (status.state === 'failed') {
            stopPolling();
            setError('Le pipeline a échoué. Vérifiez les logs Airflow.');
            setLoading(false);
          }
        } catch (err) {
          stopPolling();
          setError(String(err));
          setLoading(false);
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      setError(String(err));
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto text-center animate-in fade-in duration-500">
      <h1 className="text-3xl font-bold mb-8 text-slate-800">1. Ingestion & Traitement IA</h1>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        multiple
        className="hidden"
        onChange={(e) => onFilesSelected(e.target.files)}
      />

      <div
        onClick={() => fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="border-4 border-dashed border-slate-300 hover:border-blue-500 transition-colors p-16 rounded-2xl mb-8 bg-white cursor-pointer group flex flex-col items-center gap-4"
      >
        <FileUp size={64} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
        <p className="text-xl text-slate-600 font-medium">Glissez ou cliquez pour ajouter vos documents</p>
        <p className="text-sm text-slate-400">(PDF, PNG, JPG)</p>
      </div>

      {selectedFiles.length > 0 && (
        <div className="mb-6 text-left bg-white border border-slate-200 rounded-xl p-4">
          <p className="text-sm font-bold text-slate-500 mb-2">{selectedFiles.length} fichier(s) sélectionné(s) :</p>
          <ul className="space-y-1">
            {selectedFiles.map((f, i) => (
              <li key={i} className="text-sm text-slate-700 font-mono truncate">• {f.name}</li>
            ))}
          </ul>
        </div>
      )}

      {dagState && isLoading && (
        <p className="mb-4 text-sm text-blue-600 font-medium">
          Pipeline : <span className="font-mono">{dagState}</span>
        </p>
      )}

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2 justify-center">
          <XCircle size={18} /> {error}
        </div>
      )}

      {dagState === 'success' && !isLoading && (
        <div className="mb-4 p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-2 justify-center">
          <CheckCircle2 size={18} /> Pipeline terminé avec succès
        </div>
      )}

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