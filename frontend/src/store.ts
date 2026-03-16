import { create } from 'zustand';
import type { ProcessingResult } from './types';

interface AppState {
  currentBatch: ProcessingResult | null;
  isLoading: boolean;
  setBatch: (batch: ProcessingResult) => void;
  setLoading: (loading: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  currentBatch: null,
  isLoading: false,
  setBatch: (batch) => set({ currentBatch: batch }),
  setLoading: (loading) => set({ isLoading: loading }),
}));