import { create } from 'zustand';
import { LLMSettings, UserPreferences } from '../types';

interface SettingsState {
  llm: LLMSettings;
  preferences: UserPreferences;
  updateLLM: (settings: Partial<LLMSettings>) => void;
  updatePreferences: (prefs: Partial<UserPreferences>) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  llm: {
    provider: (import.meta.env.VITE_AI_PROVIDER as any) || 'gemini',
    apiKey: '••••••••••••••••••••',
    modelName: import.meta.env.VITE_AI_MODEL || 'gemini-3.6-flash',
    temperature: 0.2,
    maxTokens: 2048,
    baseUrl: 'http://127.0.0.1:8000/api/v1',
  },
  preferences: {
    theme: 'dark',
    preferredLanguage: 'Python',
    codeEditorFontSize: 14,
    autoFormatCode: true,
    enableStreamResponse: true,
    defaultAgentStrategy: 'auto',
  },

  updateLLM: (settings) =>
    set((state) => ({ llm: { ...state.llm, ...settings } })),

  updatePreferences: (prefs) =>
    set((state) => ({ preferences: { ...state.preferences, ...prefs } })),
}));
