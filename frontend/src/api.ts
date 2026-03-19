export interface PipelineRunResponse {
  batch_id: string;
  dag_run_id: string;
  status: string;
}

export interface ScenarioResult {
  batch_id: string;
  documents: Record<string, unknown>[];
  validation: Record<string, unknown> | null;
}

const API_BASE = "http://localhost:8000";

export async function runPipeline(files: File[]): Promise<PipelineRunResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_BASE}/pipeline/run`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Run pipeline failed: ${res.status} ${text}`);
  }

  return res.json();
}

export async function fetchAllResults(): Promise<ScenarioResult[]> {
  const res = await fetch(`${API_BASE}/results`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Fetch results failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function fetchScenarioResults(batchId: string): Promise<ScenarioResult> {
  const res = await fetch(`${API_BASE}/results/${encodeURIComponent(batchId)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Fetch scenario failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function getPipelineStatus(batchId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${API_BASE}/pipeline/status/${encodeURIComponent(batchId)}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Fetch pipeline status failed: ${res.status} ${text}`);
  }
  return res.json();
}