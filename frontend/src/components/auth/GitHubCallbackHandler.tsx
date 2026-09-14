import React, { useEffect } from 'react';
import { Loader2 } from 'lucide-react';

export const GitHubCallbackHandler: React.FC = () => {
  useEffect(() => {
    const search = window.location.search;
    const params = new URLSearchParams(search);
    const code = params.get('code');
    const state = params.get('state');
    const error = params.get('error');

    if (error) {
      window.location.href = `/settings?github_error=${encodeURIComponent(error)}`;
      return;
    }

    if (code && state) {
      // Forward to backend OAuth callback handler which exchanges code for encrypted token
      const backendUrl =
        import.meta.env.VITE_API_URL?.replace(/\/api\/v1\/?$/, '') || 'http://127.0.0.1:8000';
      window.location.href = `${backendUrl}/api/v1/integrations/github/callback${search}`;
    } else {
      window.location.href = '/settings?github_error=missing_code_or_state';
    }
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-white">
      <div className="glass-panel p-8 rounded-2xl flex flex-col items-center gap-4 max-w-sm w-full text-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
        <h2 className="text-base font-semibold">Connecting GitHub Account…</h2>
        <p className="text-xs text-slate-400">
          Please wait while we securely complete your authorization.
        </p>
      </div>
    </div>
  );
};
