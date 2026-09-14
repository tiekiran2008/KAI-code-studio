import { create } from 'zustand';

export type Theme = 'dark' | 'light' | 'ambient' | 'system';
export type AmbientIntensity = 'minimal' | 'balanced' | 'immersive';
export type FocusArea = 'editor' | 'chat' | 'explorer' | 'review' | 'agent' | 'memory' | 'general' | null;

interface ThemeState {
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
}

const THEME_KEY = 'vite-ui-theme';
const INTENSITY_KEY = 'kai-ambient-intensity';
const MOTION_KEY = 'kai-reduce-motion';
const FOCUS_SESSION_KEY = 'kai-focus-session';

const getInitialTheme = (): Theme => {
  const saved = localStorage.getItem(THEME_KEY) as Theme | null;
  if (saved && ['dark', 'light', 'ambient', 'system'].includes(saved)) {
    return saved;
  }
  return 'dark';
};

const getInitialIntensity = (): AmbientIntensity => {
  const saved = localStorage.getItem(INTENSITY_KEY) as AmbientIntensity | null;
  if (saved && ['minimal', 'balanced', 'immersive'].includes(saved)) {
    return saved;
  }
  return 'balanced';
};

const getInitialMotion = (): boolean => {
  const saved = localStorage.getItem(MOTION_KEY);
  if (saved !== null) {
    return saved === 'true';
  }
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  return false;
};

const getInitialFocusSession = (): boolean => {
  const saved = localStorage.getItem(FOCUS_SESSION_KEY);
  return saved === 'true';
};

const resolveTheme = (theme: Theme): 'dark' | 'light' | 'ambient' => {
  if (theme === 'system') {
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-color-scheme: light)').matches) {
      return 'light';
    }
    return 'dark';
  }
  return theme;
};

export const applyThemeToDOM = (
  theme: Theme,
  intensity: AmbientIntensity,
  reduceMotion: boolean,
  focusSession: boolean
) => {
  if (typeof window === 'undefined') return;
  const root = window.document.documentElement;
  const resolved = resolveTheme(theme);

  // Remove existing theme classes
  root.classList.remove('light', 'dark', 'light-mode', 'ambient-theme');

  // Apply resolved classes
  if (resolved === 'light') {
    root.classList.add('light', 'light-mode');
  } else if (resolved === 'ambient') {
    // Keep 'dark' for tailwind class compatibility and add 'ambient-theme'
    root.classList.add('dark', 'ambient-theme');
  } else {
    root.classList.add('dark');
  }

  // Set data attributes for fine-grained CSS targeting
  root.setAttribute('data-theme', resolved);
  root.setAttribute('data-ambient-intensity', intensity);
  root.setAttribute('data-reduce-motion', String(reduceMotion));
  root.setAttribute('data-focus-session', String(focusSession && resolved === 'ambient'));
};

export const useThemeStore = create<ThemeState>((set, get) => {
  const initialTheme = getInitialTheme();
  const initialIntensity = getInitialIntensity();
  const initialMotion = getInitialMotion();
  const initialFocusSession = getInitialFocusSession();

  // Initial apply to DOM
  if (typeof window !== 'undefined') {
    applyThemeToDOM(initialTheme, initialIntensity, initialMotion, initialFocusSession);
  }

  return {
    theme: initialTheme,
    resolvedTheme: resolveTheme(initialTheme),
    ambientIntensity: initialIntensity,
    reduceMotion: initialMotion,
    focusSession: initialFocusSession,
    activeFocusArea: null,

    setTheme: (newTheme: Theme) => {
      localStorage.setItem(THEME_KEY, newTheme);
      const { ambientIntensity, reduceMotion, focusSession } = get();
      applyThemeToDOM(newTheme, ambientIntensity, reduceMotion, focusSession);
      set({
        theme: newTheme,
        resolvedTheme: resolveTheme(newTheme),
      });
    },

    setAmbientIntensity: (intensity: AmbientIntensity) => {
      localStorage.setItem(INTENSITY_KEY, intensity);
      const { theme, reduceMotion, focusSession } = get();
      applyThemeToDOM(theme, intensity, reduceMotion, focusSession);
      set({ ambientIntensity: intensity });
    },

    setReduceMotion: (reduce: boolean) => {
      localStorage.setItem(MOTION_KEY, String(reduce));
      const { theme, ambientIntensity, focusSession } = get();
      applyThemeToDOM(theme, ambientIntensity, reduce, focusSession);
      set({ reduceMotion: reduce });
    },

    setFocusSession: (active: boolean) => {
      localStorage.setItem(FOCUS_SESSION_KEY, String(active));
      const { theme, ambientIntensity, reduceMotion } = get();
      applyThemeToDOM(theme, ambientIntensity, reduceMotion, active);
      set({ focusSession: active });
    },

    setActiveFocusArea: (area: FocusArea) => {
      set({ activeFocusArea: area });
    },
  };
});
