/**
 * Airflow + MongoDB API helpers.
 *
 * In production the nginx reverse-proxy forwards /api/v1 and /mongo_api
 * to the Airflow webserver.  In dev, Vite does the same via proxy config.
 */

const AIRFLOW_AUTH = btoa("admin:admin"); // Basic auth header

const headers = (): HeadersInit => ({
  "Content-Type": "application/json",
  Authorization: `Basic ${AIRFLOW_AUTH}`,
});

/* ------------------------------------------------------------------ */
/*  Airflow REST API                                                   */
/* ------------------------------------------------------------------ */

const DAG_ID = "hkt_mia_pipeline";

export interface DagRun {
  dag_run_id: string;
  state: "queued" | "running" | "success" | "failed";
}

/** Trigger a new DAG run and return the run metadata. */
export async function triggerDag(): Promise<DagRun> {
  const res = await fetch(`/api/v1/dags/${DAG_ID}/dagRuns`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Trigger failed: ${res.status}`);
  return res.json();
}

/** Get the current state of a DAG run. */
export async function getDagRunStatus(dagRunId: string): Promise<DagRun> {
  const res = await fetch(
    `/api/v1/dags/${DAG_ID}/dagRuns/${encodeURIComponent(dagRunId)}`,
    { headers: headers() }
  );
  if (!res.ok) throw new Error(`Status check failed: ${res.status}`);
  return res.json();
}

/* ------------------------------------------------------------------ */
/*  MongoDB plugin API                                                 */
/* ------------------------------------------------------------------ */

export interface ScenarioResult {
  documents: Record<string, unknown>[];
  validation: Record<string, unknown> | null;
}

/** Fetch processed results for all scenarios. */
export async function fetchAllResults(): Promise<{
  documents: Record<string, unknown>[];
  validations: Record<string, unknown>[];
}> {
  const res = await fetch("/mongo_api/results", { headers: headers() });
  if (!res.ok) throw new Error(`Fetch results failed: ${res.status}`);
  return res.json();
}

/** Fetch processed results for a single scenario. */
export async function fetchScenarioResults(
  scenario: string
): Promise<ScenarioResult> {
  const res = await fetch(`/mongo_api/results/${encodeURIComponent(scenario)}`, {
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Fetch scenario failed: ${res.status}`);
  return res.json();
}

/** List available scenario names. */
export async function fetchScenarios(): Promise<string[]> {
  const res = await fetch("/mongo_api/scenarios", { headers: headers() });
  if (!res.ok) throw new Error(`Fetch scenarios failed: ${res.status}`);
  return res.json();
}
