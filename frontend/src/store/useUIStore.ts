import { create } from 'zustand';
import { useThemeStore } from './useThemeStore';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface UIState {
  theme: 'dark' | 'light' | 'ambient';
  sidebarCollapsed: boolean;
  commandPaletteOpen: boolean;
  activeModal: string | null;
  toasts: Toast[];
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setActiveModal: (modal: string | null) => void;
  addToast: (message: string, type?: 'success' | 'error' | 'info') => void;
  removeToast: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  theme: (useThemeStore.getState().resolvedTheme || 'dark'),
  sidebarCollapsed: false,
  commandPaletteOpen: false,
  activeModal: null,
  toasts: [],
  toggleTheme: () => {
    const current = useThemeStore.getState().theme;
    const next = current === 'dark' ? 'ambient' : current === 'ambient' ? 'light' : 'dark';
    useThemeStore.getState().setTheme(next);
    set({ theme: next as 'dark' | 'light' | 'ambient' });
  },
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setActiveModal: (modal) => set({ activeModal: modal }),
  addToast: (message, type = 'info') => {
    const id = `toast-${Date.now()}`;
    set((state) => ({ toasts: [...state.toasts, { id, type, message }] }));
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    }, 4000);
  },
  removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));

// Subscribe to useThemeStore updates to keep useUIStore in sync
useThemeStore.subscribe((state) => {
  useUIStore.setState({ theme: state.resolvedTheme });
});
