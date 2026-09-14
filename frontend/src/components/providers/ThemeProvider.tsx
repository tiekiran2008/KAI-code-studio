import React, { createContext, useContext, useEffect } from 'react';
import { useThemeStore, Theme, AmbientIntensity, FocusArea } from '../../store/useThemeStore';

export type { Theme, AmbientIntensity, FocusArea };

interface ThemeContextValue {
  theme: Theme;
  resolvedTheme: 'dark' | 'light' | 'ambient';
  ambientIntensity: AmbientIntensity;
  reduceMotion: boolean;
  focusSession: boolean;
  activeFocusArea: FocusArea;
  setTheme: (theme: Theme) => void;
  setAmbientIntensity: (intensity: AmbientIntensity) => void;
  setReduceMotion: (reduce: boolean) => void;
  setFocusSession: (active: boolean) => void;
  setActiveFocusArea: (area: FocusArea) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
}

export function ThemeProvider({ children }: ThemeProviderProps) {
  const themeState = useThemeStore();

  useEffect(() => {
    // Listen to system preference changes if system theme is selected
    if (themeState.theme === 'system' && typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        themeState.setTheme('system');
      };
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [themeState.theme]);

  const toggleTheme = () => {
    if (themeState.theme === 'dark') {
      themeState.setTheme('ambient');
    } else if (themeState.theme === 'ambient') {
      themeState.setTheme('light');
    } else {
      themeState.setTheme('dark');
    }
  };

  const value: ThemeContextValue = {
    ...themeState,
    toggleTheme,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    // Fallback to store if used outside provider
    const state = useThemeStore.getState();
    return {
      ...state,
      toggleTheme: () => {
        const next = state.theme === 'dark' ? 'ambient' : state.theme === 'ambient' ? 'light' : 'dark';
        state.setTheme(next);
      }
    };
  }
  return context;
};
