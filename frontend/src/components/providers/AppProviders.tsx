import React, { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './ThemeProvider';
import { ToastProvider } from '../common/ToastProvider';
import { supabase, isSupabaseConfigured } from '../../lib/supabase';
import { useAuthStore } from '../../store/authStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const AuthSync: React.FC = () => {
  const { setOAuthSession } = useAuthStore();

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) return;

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'TOKEN_REFRESHED' || event === 'SIGNED_IN') {
        if (session && session.user) {
          setOAuthSession({
            access_token: session.access_token,
            refresh_token: session.refresh_token,
            expires_in: session.expires_in,
            user: {
              id: session.user.id,
              email: session.user.email || '',
              created_at: session.user.created_at || new Date().toISOString(),
            },
          });
        }
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [setOAuthSession]);

  return null;
};

export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="dark">
        <AuthSync />
        {children}
        <ToastProvider />
      </ThemeProvider>
    </QueryClientProvider>
  );
};
