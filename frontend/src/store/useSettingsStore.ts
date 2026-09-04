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
    provider: 'gemini',
    apiKey: '••••••••••••••••••••',
    modelName: 'gemini-3.1-pro',
    temperature: 0.2,
    maxTokens: 2048,
    baseUrl: 'http://localhost:8000/api/v1',
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
