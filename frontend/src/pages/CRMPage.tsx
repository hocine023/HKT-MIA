import { useStore } from "../store";
import { Database } from "lucide-react";

export const CRMPage = () => {
  const { currentBatch } = useStore();

  console.log("CRM currentBatch =", currentBatch);

  const docs = Array.isArray(currentBatch?.documents)
    ? currentBatch.documents
    : [];

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-8 border-b pb-4">
        <Database className="text-blue-600" size={32} />
        <h1 className="text-2xl font-bold text-slate-800">
          2. CRM - Fiches Fournisseurs
        </h1>
      </div>

      {!currentBatch ? (
        <div className="bg-white p-6 rounded-xl border">
          <p className="text-slate-500">Aucun batch chargé dans le store.</p>
        </div>
      ) : docs.length === 0 ? (
        <div className="bg-white p-6 rounded-xl border">
          <p className="text-slate-500">
            Batch chargé, mais aucun document disponible.
          </p>

          <pre className="mt-4 bg-slate-50 rounded-xl p-4 text-xs overflow-auto">
            {JSON.stringify(currentBatch, null, 2)}
          </pre>
        </div>
      ) : (
        <div className="space-y-6">
          {docs.map((doc: any, index: number) => {
            const fields = doc?.extracted_fields ?? {};
            const displayName =
              fields?.emetteur || fields?.fournisseur || "-";

            return (
              <div
                key={doc?.document_id ?? index}
                className="bg-white p-8 rounded-xl shadow-sm border border-slate-200"
              >
                <h3 className="text-sm font-bold text-blue-600 uppercase tracking-wider mb-4">
                  {doc?.document_type || "document"} — {doc?.document_id || index}
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Raison Sociale
                    </label>
                    <p className="text-lg font-semibold text-slate-900">
                      {displayName}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      SIRET
                    </label>
                    <p className="text-lg font-mono text-slate-900">
                      {fields?.siret ?? "-"}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      SIREN
                    </label>
                    <p className="text-lg font-mono text-slate-900">
                      {fields?.siren ?? "-"}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Client
                    </label>
                    <p className="text-lg text-slate-900">
                      {fields?.client ?? "-"}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Montant HT
                    </label>
                    <p className="text-lg text-slate-900">
                      {fields?.sous_total_ht != null ? `${fields.sous_total_ht} €` : "-"}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Montant TTC
                    </label>
                    <p className="text-lg text-slate-900">
                      {fields?.total_ttc != null ? `${fields.total_ttc} €` : "-"}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Date
                    </label>
                    <p className="text-lg text-slate-900">
                      {fields?.date ?? "-"}
                    </p>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                      Type document
                    </label>
                    <p className="text-lg text-slate-900">
                      {doc?.document_type ?? "-"}
                    </p>
                  </div>
                </div>

                <details className="mt-6">
                  <summary className="cursor-pointer text-sm text-slate-500">
                    Voir JSON brut
                  </summary>
                  <pre className="mt-3 bg-slate-50 rounded-xl p-4 text-xs overflow-auto">
                    {JSON.stringify(doc, null, 2)}
                  </pre>
                </details>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};