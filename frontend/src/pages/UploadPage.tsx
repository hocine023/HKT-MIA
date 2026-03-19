import { useStore } from "../store";
import { useNavigate } from "react-router-dom";
import { FileUp, Loader2, CheckCircle2, XCircle } from "lucide-react";
import {
  runPipeline,
  getPipelineStatus,
  fetchScenarioResults,
  fetchAllResults,
} from "../api";
import { useRef, useState, useCallback } from "react";

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 30;

export const UploadPage = () => {
  const { setBatch, isLoading, setLoading, error, setError } = useStore();
  const navigate = useNavigate();
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [pipelineState, setPipelineState] = useState<string | null>(null);
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);

  const onFilesSelected = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;
    setSelectedFiles(Array.from(files));
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      onFilesSelected(e.dataTransfer.files);
    },
    [onFilesSelected]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  const mapScenarioResultToStoreBatch = (scenarioResult: any) => {
    return {
      batch_id: scenarioResult.batch_id,
      documents: scenarioResult.documents ?? [],
      validation: scenarioResult.validation ?? {
        global_status: "a_verifier",
        anomalies: [],
        checks: [],
      },
    };
  };

  const handleProcess = async () => {
    if (selectedFiles.length === 0) {
      setError("Veuillez sélectionner 3 fichiers avant de lancer le pipeline.");
      return;
    }

    setLoading(true);
    setError(null);
    setPipelineState("uploading");

    try {
      const run = await runPipeline(selectedFiles);
      setCurrentBatchId(run.batch_id);
      setPipelineState(run.status || "queued");

      let attempts = 0;

      pollingRef.current = setInterval(async () => {
        try {
          attempts += 1;

          const status = await getPipelineStatus(run.batch_id);
          const state = String(status.status ?? "running");
          setPipelineState(state);

          if (state === "finished") {
            stopPolling();

            const scenarioResult = await fetchScenarioResults(run.batch_id);
            setBatch(mapScenarioResultToStoreBatch(scenarioResult));

            // refresh global list if your store/page uses it later
            await fetchAllResults();

            setLoading(false);
            navigate("/crm");
            return;
          }

          if (attempts >= MAX_POLL_ATTEMPTS) {
            stopPolling();
            setError("Le pipeline est toujours en cours. Réessayez dans quelques instants.");
            setLoading(false);
          }
        } catch (err) {
          stopPolling();
          setError(err instanceof Error ? err.message : "Erreur pendant le polling du pipeline.");
          setLoading(false);
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      stopPolling();
      setError(err instanceof Error ? err.message : "Erreur au lancement du pipeline.");
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto text-center animate-in fade-in duration-500">
      <h1 className="text-3xl font-bold mb-8 text-slate-800">
        1. Ingestion & Traitement IA
      </h1>

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
        <FileUp
          size={64}
          className="text-slate-400 group-hover:text-blue-500 transition-colors"
        />
        <p className="text-xl text-slate-600 font-medium">
          Glissez ou cliquez pour ajouter vos documents
        </p>
        <p className="text-sm text-slate-400">(PDF, PNG, JPG)</p>
      </div>

      {selectedFiles.length > 0 && (
        <div className="mb-6 text-left bg-white border border-slate-200 rounded-xl p-4">
          <p className="text-sm font-bold text-slate-500 mb-2">
            {selectedFiles.length} fichier(s) sélectionné(s) :
          </p>
          <ul className="space-y-1">
            {selectedFiles.map((f, i) => (
              <li key={i} className="text-sm text-slate-700 font-mono truncate">
                • {f.name}
              </li>
            ))}
          </ul>
        </div>
      )}

      {pipelineState && isLoading && (
        <p className="mb-4 text-sm text-blue-600 font-medium">
          Pipeline : <span className="font-mono">{pipelineState}</span>
        </p>
      )}

      {currentBatchId && (
        <p className="mb-4 text-sm text-slate-500">
          Batch ID : <span className="font-mono">{currentBatchId}</span>
        </p>
      )}

      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-2 justify-center">
          <XCircle size={18} /> {error}
        </div>
      )}

      {pipelineState === "finished" && !isLoading && (
        <div className="mb-4 p-4 bg-green-50 text-green-700 rounded-lg flex items-center gap-2 justify-center">
          <CheckCircle2 size={18} /> Pipeline terminé avec succès
        </div>
      )}

      <button
        onClick={handleProcess}
        disabled={isLoading}
        className="px-8 py-4 bg-blue-600 text-white font-bold rounded-xl shadow-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-3 mx-auto transition-all"
      >
        {isLoading ? (
          <>
            <Loader2 className="animate-spin" />
            Traitement en cours...
          </>
        ) : (
          "Lancer le pipeline"
        )}
      </button>
    </div>
  );
};