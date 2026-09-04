import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi, UserSession, User } from '../api/auth';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<UserSession>;
  logout: () => Promise<void>;
  refreshAuthToken: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const session = await authApi.login(email, password);
          set({
            user: session.user,
            accessToken: session.access_token || null,
            refreshToken: session.refresh_token || null,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: any) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },

      signup: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const session = await authApi.signup(email, password);
          if (session.access_token && session.refresh_token) {
            set({
              user: session.user,
              accessToken: session.access_token,
              refreshToken: session.refresh_token,
              isAuthenticated: true,
              isLoading: false,
            });
          } else {
            set({
              user: session.user,
              accessToken: null,
              refreshToken: null,
              isAuthenticated: false,
              isLoading: false,
            });
          }
          return session;
        } catch (error: any) {
          set({ error: error.message, isLoading: false });
          throw error;
        }
      },


      logout: async () => {
        const { accessToken } = get();
        if (accessToken) {
          try {
            await authApi.logout(accessToken);
          } catch (error) {
            console.error('Logout error:', error);
          }
        }
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      refreshAuthToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) {
          set({ isAuthenticated: false, user: null, accessToken: null });
          return;
        }
        
        try {
          const session = await authApi.refreshToken(refreshToken);
          set({
            user: session.user,
            accessToken: session.access_token,
            refreshToken: session.refresh_token,
            isAuthenticated: true,
          });
        } catch (error) {
          console.error('Token refresh failed:', error);
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          });
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        accessToken: state.accessToken, 
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);
