import { create } from "zustand";
import type { ProcessingResult } from "./types";

interface AppState {
  currentBatch: ProcessingResult | null;
  isLoading: boolean;
  dagRunId: string | null;
  dagState: string | null;
  error: string | null;
  setBatch: (batch: ProcessingResult) => void;
  setLoading: (loading: boolean) => void;
  setDagRun: (id: string | null, state: string | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useStore = create<AppState>((set) => ({
  currentBatch: null,
  isLoading: false,
  dagRunId: null,
  dagState: null,
  error: null,

  setBatch: (batch) => set({ currentBatch: batch }),

  setLoading: (loading) => set({ isLoading: loading }),

  setDagRun: (id, state) =>
    set({
      dagRunId: id,
      dagState: state,
    }),

  setError: (error) => set({ error }),

  reset: () =>
    set({
      currentBatch: null,
      isLoading: false,
      dagRunId: null,
      dagState: null,
      error: null,
    }),
}));