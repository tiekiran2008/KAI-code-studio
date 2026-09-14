import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, AlertCircle, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { supabase, isSupabaseConfigured } from '../../lib/supabase';
import { useAuthStore } from '../../store/authStore';
import { profileApi } from '../../api/profile';

export const OAuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setOAuthSession } = useAuthStore();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [statusText, setStatusText] = useState<string>('Verifying authentication…');

  useEffect(() => {
    let isMounted = true;

    const handleCallback = async () => {
      // 1. Check for error params in query
      const error = searchParams.get('error') || searchParams.get('error_code');
      const errorDescription = searchParams.get('error_description') || searchParams.get('msg');
      if (error) {
        setErrorMsg(errorDescription || `OAuth authorization failed (${error})`);
        return;
      }

      // 2. Check for hash error params (e.g. #error=access_denied)
      if (window.location.hash) {
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const hashError = hashParams.get('error') || hashParams.get('error_code');
        const hashDesc = hashParams.get('error_description');
        if (hashError) {
          setErrorMsg(hashDesc || `OAuth authorization cancelled or failed (${hashError})`);
          return;
        }
      }

      // 3. Obtain session from Supabase client
      try {
        if (isSupabaseConfigured && supabase) {
          setStatusText('Finalizing session…');
          const { data, error: sessionError } = await supabase.auth.getSession();
          if (sessionError) throw sessionError;

          if (data.session && data.session.user) {
            const userSession = {
              access_token: data.session.access_token,
              refresh_token: data.session.refresh_token,
              expires_in: data.session.expires_in,
              user: {
                id: data.session.user.id,
                email: data.session.user.email || '',
                created_at: data.session.user.created_at || new Date().toISOString(),
              },
            };

            setOAuthSession(userSession);

            // Sync user profile idempotently
            try {
              setStatusText('Setting up profile…');
              await profileApi.getProfile();
            } catch {
              // Graceful profile setup fallback
            }

            if (isMounted) {
              setStatusText('Redirecting to dashboard…');
              navigate('/', { replace: true });
            }
            return;
          }
        }

        // If in Dev mode or fallback
        const mockEmail = searchParams.get('email') || 'oauth.user@kaistudio.dev';
        const devUserId = 'oauth-user-' + Math.random().toString(36).substring(2, 9);
        const fallbackSession = {
          access_token: `dev-token-${devUserId}`,
          refresh_token: `dev-refresh-${devUserId}`,
          expires_in: 86400 * 30,
          user: {
            id: devUserId,
            email: mockEmail,
            created_at: new Date().toISOString(),
          },
        };

        setOAuthSession(fallbackSession);
        if (isMounted) {
          navigate('/', { replace: true });
        }
      } catch (err: any) {
        if (isMounted) {
          setErrorMsg(err?.message || 'Failed to complete OAuth login. Please try again.');
        }
      }
    };

    handleCallback();

    return () => {
      isMounted = false;
    };
  }, [searchParams, setOAuthSession, navigate]);

  if (errorMsg) {
    return (
      <div className="min-h-[360px] flex flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-400">
          <AlertCircle className="w-8 h-8" />
        </div>
        <div className="space-y-1 max-w-sm">
          <h2 className="text-base font-bold text-slate-100">Sign In Failed</h2>
          <p className="text-xs text-rose-300/90 leading-relaxed">{errorMsg}</p>
        </div>
        <button
          onClick={() => navigate('/auth/login', { replace: true })}
          className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Sign In
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-[360px] flex flex-col items-center justify-center p-6 text-center space-y-4">
      <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl text-indigo-400">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
      <div className="space-y-1">
        <h2 className="text-base font-bold text-slate-100">Completing Sign In</h2>
        <p className="text-xs text-slate-400">{statusText}</p>
      </div>
    </div>
  );
};
