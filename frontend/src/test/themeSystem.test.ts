import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useThemeStore, applyThemeToDOM } from '../store/useThemeStore';

describe('Signature Theme System: Ambient Focus & Theme Switching', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
    // Reset store to dark
    useThemeStore.setState({
      theme: 'dark',
      resolvedTheme: 'dark',
      ambientIntensity: 'balanced',
      reduceMotion: false,
      focusSession: false,
      activeFocusArea: null,
    });
  });

  it('1. Initializes with default dark theme when no saved preference exists', () => {
    const state = useThemeStore.getState();
    expect(state.theme).toBe('dark');
    expect(state.resolvedTheme).toBe('dark');
    expect(state.ambientIntensity).toBe('balanced');
  });

  it('2. Switches to Ambient Focus theme, updating DOM attributes and classes', () => {
    useThemeStore.getState().setTheme('ambient');

    const state = useThemeStore.getState();
    expect(state.theme).toBe('ambient');
    expect(state.resolvedTheme).toBe('ambient');
    expect(localStorage.getItem('vite-ui-theme')).toBe('ambient');

    const root = document.documentElement;
    expect(root.classList.contains('ambient-theme')).toBe(true);
    expect(root.classList.contains('dark')).toBe(true);
    expect(root.classList.contains('light')).toBe(false);
    expect(root.getAttribute('data-theme')).toBe('ambient');
  });

  it('3. Switches to Light theme, updating DOM attributes and classes cleanly', () => {
    useThemeStore.getState().setTheme('light');

    const state = useThemeStore.getState();
    expect(state.theme).toBe('light');
    expect(state.resolvedTheme).toBe('light');
    expect(localStorage.getItem('vite-ui-theme')).toBe('light');

    const root = document.documentElement;
    expect(root.classList.contains('light')).toBe(true);
    expect(root.classList.contains('light-mode')).toBe(true);
    expect(root.classList.contains('dark')).toBe(false);
    expect(root.classList.contains('ambient-theme')).toBe(false);
    expect(root.getAttribute('data-theme')).toBe('light');
  });

  it('4. Updates Ambient Intensity (minimal, balanced, immersive) and persists to localStorage', () => {
    useThemeStore.getState().setTheme('ambient');
    useThemeStore.getState().setAmbientIntensity('immersive');

    expect(useThemeStore.getState().ambientIntensity).toBe('immersive');
    expect(localStorage.getItem('kai-ambient-intensity')).toBe('immersive');
    expect(document.documentElement.getAttribute('data-ambient-intensity')).toBe('immersive');

    useThemeStore.getState().setAmbientIntensity('minimal');
    expect(useThemeStore.getState().ambientIntensity).toBe('minimal');
    expect(localStorage.getItem('kai-ambient-intensity')).toBe('minimal');
    expect(document.documentElement.getAttribute('data-ambient-intensity')).toBe('minimal');
  });

  it('5. Toggles Focus Session mode in Ambient Focus and updates DOM', () => {
    useThemeStore.getState().setTheme('ambient');
    useThemeStore.getState().setFocusSession(true);

    expect(useThemeStore.getState().focusSession).toBe(true);
    expect(localStorage.getItem('kai-focus-session')).toBe('true');
    expect(document.documentElement.getAttribute('data-focus-session')).toBe('true');

    useThemeStore.getState().setFocusSession(false);
    expect(useThemeStore.getState().focusSession).toBe(false);
    expect(localStorage.getItem('kai-focus-session')).toBe('false');
    expect(document.documentElement.getAttribute('data-focus-session')).toBe('false');
  });

  it('6. Toggles Reduce Motion and persists preference', () => {
    useThemeStore.getState().setReduceMotion(true);

    expect(useThemeStore.getState().reduceMotion).toBe(true);
    expect(localStorage.getItem('kai-reduce-motion')).toBe('true');
    expect(document.documentElement.getAttribute('data-reduce-motion')).toBe('true');
  });

  it('7. Tracks active Focus Area (editor, chat, review, agent)', () => {
    useThemeStore.getState().setActiveFocusArea('editor');
    expect(useThemeStore.getState().activeFocusArea).toBe('editor');

    useThemeStore.getState().setActiveFocusArea('chat');
    expect(useThemeStore.getState().activeFocusArea).toBe('chat');

    useThemeStore.getState().setActiveFocusArea(null);
    expect(useThemeStore.getState().activeFocusArea).toBe(null);
  });
});
