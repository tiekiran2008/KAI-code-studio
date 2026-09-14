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
  loginWithOAuth: (provider: 'google' | 'github') => Promise<void>;
  setOAuthSession: (session: UserSession) => void;
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

      loginWithOAuth: async (provider: 'google' | 'github') => {
        console.log(`[OAuth] Button clicked — provider: ${provider}`);
        set({ isLoading: true, error: null });
        try {
          console.log('[OAuth] Importing Supabase client...');
          const { supabase, isSupabaseConfigured } = await import('../lib/supabase');
          console.log('[OAuth] Supabase configured:', isSupabaseConfigured);

          if (supabase && isSupabaseConfigured) {
            // Always redirect to 127.0.0.1 so the URL matches the Supabase
            // allow-list regardless of whether the user opened localhost or 127.0.0.1.
            const redirectTo = `${window.location.protocol}//127.0.0.1:${window.location.port || '3000'}/auth/callback`;
            console.log('[OAuth] Calling signInWithOAuth, redirectTo:', redirectTo);

            const { error } = await supabase.auth.signInWithOAuth({
              provider,
              options: { redirectTo },
            });

            if (error) {
              console.error('[OAuth] Supabase returned error:', error.message);
              throw error;
            }
            // If no error, Supabase will redirect the browser — no further action needed here.
            console.log('[OAuth] signInWithOAuth succeeded — browser redirect in progress.');
          } else {
            // Supabase is not configured: surface a clear, visible error instead of
            // silently pretending to sign in with a fake mock session.
            const msg = `Google/GitHub sign-in requires Supabase. The app's Supabase credentials (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY) are missing or empty. Rebuild the frontend with the correct values.`;
            console.error('[OAuth] Supabase client is null —', msg);
            throw new Error(msg);
          }
        } catch (error: any) {
          set({ error: error.message || `Failed to sign in with ${provider}`, isLoading: false });
          throw error;
        }
      },

      setOAuthSession: (session: UserSession) => {
        set({
          user: session.user,
          accessToken: session.access_token || null,
          refreshToken: session.refresh_token || null,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
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
        try {
          const { supabase } = await import('../lib/supabase');
          if (supabase) {
            await supabase.auth.signOut().catch(() => {});
          }
        } catch {
          // Ignore supabase import/signout error in mock/offline mode
        }

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
