import { useStore } from "../store";
import { ShieldAlert, AlertTriangle, CheckCircle2 } from "lucide-react";

export const CompliancePage = () => {
  const { currentBatch } = useStore();

  if (!currentBatch || !currentBatch.validation) {
    return (
      <div className="p-8 text-center text-slate-500">
        Aucune donnée de conformité disponible.
      </div>
    );
  }

  const validation = currentBatch.validation;
  const status =
    validation.global_status ||
    validation.status ||
    "a_verifier";

  const anomalies: string[] = Array.isArray(validation.anomalies)
    ? validation.anomalies.map((a: any) =>
        typeof a === "string" ? a : a?.message || a?.description || JSON.stringify(a)
      )
    : [];

  const checks: any[] = Array.isArray(validation.checks)
    ? validation.checks
    : [];

  const isConforme = status === "conforme";
  const isWarning = status === "à vérifier" || status === "a_verifier";

  return (
    <div className="p-8 max-w-4xl mx-auto animate-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-8 border-b pb-4">
        <ShieldAlert
          className={
            isConforme
              ? "text-green-600"
              : isWarning
              ? "text-amber-500"
              : "text-red-600"
          }
          size={32}
        />
        <h1 className="text-2xl font-bold text-slate-800">
          3. Outil de Conformité
        </h1>
      </div>

      <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
        <div className="flex items-center gap-4 mb-8">
          <span className="text-lg font-semibold text-slate-600">
            Statut global :
          </span>
          <span
            className={`px-4 py-2 rounded-full text-sm font-bold uppercase tracking-wider flex items-center gap-2 ${
              isConforme
                ? "bg-green-100 text-green-700"
                : isWarning
                ? "bg-amber-100 text-amber-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {isConforme ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            {String(status).replace("_", " ")}
          </span>
        </div>

        {checks.length > 0 && (
          <div className="mb-8">
            <h3 className="font-bold text-slate-800 mb-4">Contrôles exécutés</h3>
            <div className="space-y-3">
              {checks.map((check, idx) => {
                const checkStatus = check.status || "not_applicable";
                const passed = checkStatus === "passed";
                const failed = checkStatus === "failed";

                return (
                  <div
                    key={idx}
                    className={`p-4 rounded-lg border ${
                      passed
                        ? "bg-green-50 border-green-100 text-green-800"
                        : failed
                        ? "bg-red-50 border-red-100 text-red-800"
                        : "bg-slate-50 border-slate-200 text-slate-700"
                    }`}
                  >
                    <p className="font-semibold">{check.rule || `Règle ${idx + 1}`}</p>
                    <p className="text-sm mt-1">{check.message || "-"}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {anomalies.length > 0 ? (
          <div className="space-y-4">
            <h3 className="font-bold text-slate-800 flex items-center gap-2">
              <AlertTriangle className="text-amber-500" size={20} />
              Incohérences détectées ({anomalies.length})
            </h3>
            <ul className="space-y-3">
              {anomalies.map((anomalie, idx) => (
                <li
                  key={idx}
                  className="p-4 bg-red-50 text-red-800 rounded-lg border border-red-100 flex items-start gap-3 font-medium"
                >
                  <span className="mt-1 h-2 w-2 bg-red-500 rounded-full flex-shrink-0" />
                  {anomalie}
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="p-4 bg-green-50 text-green-800 rounded-lg border border-green-100">
            Aucune anomalie détectée.
          </div>
        )}
      </div>
    </div>
  );
};