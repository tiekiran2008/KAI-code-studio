import React, { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSettingsStore } from '../store/useSettingsStore';
import { useUIStore } from '../store/useUIStore';
import { useGitHubStore } from '../store/useGitHubStore';
import {
  Settings,
  Cpu,
  Sun,
  Moon,
  CheckCircle2,
  Sliders,
  Save,
  Github,
  Link2Off,
  Loader2,
  AlertCircle,
  ExternalLink,
  User,
  Clock,
} from 'lucide-react';

// ─── GitHub Integration Panel ─────────────────────────────────────────────────

const GitHubIntegrationPanel: React.FC = () => {
  const {
    status,
    isStatusLoading,
    statusError,
    isConnecting,
    isDisconnecting,
    fetchStatus,
    startOAuthFlow,
    disconnect,
  } = useGitHubStore();
  const { addToast } = useUIStore();
  const [searchParams, setSearchParams] = useSearchParams();

  // Handle callback query parameters injected by the backend OAuth redirect
  useEffect(() => {
    const githubParam = searchParams.get('github');
    const githubError = searchParams.get('github_error');

    if (githubParam === 'connected') {
      addToast('GitHub account connected successfully!', 'success');
      // Clean the URL without refreshing the page
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.delete('github');
        return next;
      });
      fetchStatus();
    } else if (githubError) {
      const messages: Record<string, string> = {
        invalid_state: 'OAuth state mismatch — possible CSRF attempt or session expired.',
        missing_code_or_state: 'GitHub did not return a valid authorization code.',
        connection_failed: 'GitHub token exchange failed. Please try again.',
      };
      addToast(messages[githubError] || `GitHub connection failed: ${githubError}`, 'error');
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.delete('github_error');
        return next;
      });
    }
  }, [searchParams, setSearchParams, addToast, fetchStatus]);

  // Fetch status on mount
  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleDisconnect = async () => {
    await disconnect();
    addToast('GitHub account disconnected.', 'success');
  };

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      <h2 className="text-base font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
        <Github className="w-4 h-4 text-slate-300" /> GitHub Integration
      </h2>

      {statusError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" /> {statusError}
        </div>
      )}

      {isStatusLoading ? (
        <div className="flex items-center gap-2 text-slate-400 text-xs py-2">
          <Loader2 className="w-4 h-4 animate-spin" /> Checking connection…
        </div>
      ) : status?.connected ? (
        /* ── Connected State ── */
        <div className="space-y-4">
          <div className="flex items-center gap-4 p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/20">
            {status.avatar_url ? (
              <img
                src={status.avatar_url}
                alt={status.username || 'GitHub User'}
                className="w-10 h-10 rounded-full border border-emerald-500/30"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
                <User className="w-5 h-5 text-slate-400" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                {status.username || 'GitHub Account'}
              </p>
              {status.connected_at && (
                <p className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Connected {new Date(status.connected_at).toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric',
                  })}
                </p>
              )}
            </div>
            <a
              href={`https://github.com/${status.username}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-white transition-colors"
              title="View GitHub profile"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Your GitHub account is connected. KAI Code Studio can now browse and import your
            private and public repositories, and create pull requests on your behalf via the
            AI code review system.
          </p>

          <button
            type="button"
            onClick={handleDisconnect}
            disabled={isDisconnecting}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-950/30 border border-rose-500/30 hover:bg-rose-950/60 text-rose-400 text-xs font-semibold transition-all disabled:opacity-60"
          >
            {isDisconnecting ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Disconnecting…</>
            ) : (
              <><Link2Off className="w-3.5 h-3.5" /> Disconnect GitHub Account</>
            )}
          </button>
        </div>
      ) : (
        /* ── Disconnected State ── */
        <div className="space-y-4">
          <p className="text-xs text-slate-400 leading-relaxed">
            Connect your GitHub account to browse private repositories, skip manual URL entry, and
            enable automated pull request creation from AI code reviews.
          </p>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 space-y-1.5">
            <p className="font-semibold text-slate-300">Permissions requested:</p>
            <ul className="list-disc list-inside space-y-0.5 text-slate-500">
              <li><span className="font-mono text-slate-400">repo</span> — read/write access to repositories</li>
              <li><span className="font-mono text-slate-400">read:user</span> — read public profile data</li>
              <li><span className="font-mono text-slate-400">user:email</span> — read primary email address</li>
            </ul>
          </div>
          <button
            type="button"
            onClick={startOAuthFlow}
            disabled={isConnecting}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-sm font-semibold shadow-glow transition-all disabled:opacity-60"
          >
            {isConnecting ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Redirecting to GitHub…</>
            ) : (
              <><Github className="w-4 h-4" /> Connect GitHub Account</>
            )}
          </button>
          <p className="text-[11px] text-slate-500">
            Your access token is encrypted at rest using AES-128-CBC (Fernet) and never exposed to
            the frontend or logs.
          </p>
        </div>
      )}
    </div>
  );
};

// ─── Main Settings Page ───────────────────────────────────────────────────────

export const SettingsPage: React.FC = () => {
  const { llm, preferences, updateLLM, updatePreferences } = useSettingsStore();
  const { theme, toggleTheme, addToast } = useUIStore();

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    addToast('Settings saved successfully!', 'success');
  };

  return (
    <div className="max-w-4xl space-y-6 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-indigo-400" /> Platform Configuration
          </h1>
          <p className="text-xs text-slate-400">
            Configure LLM execution providers, API endpoint base URLs, code editor themes, and agent routing preferences.
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* LLM Provider Configuration */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
            <Cpu className="w-4 h-4 text-indigo-400" /> LLM Provider &amp; Model Settings
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">Provider</label>
              <select
                value={llm.provider}
                onChange={(e) => updateLLM({ provider: e.target.value as any })}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="gemini">Google Gemini Pro (Default)</option>
                <option value="openai">OpenAI GPT-4o</option>
                <option value="anthropic">Anthropic Claude 3.5 Sonnet</option>
                <option value="ollama">Ollama (Local LLM)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">Model Identifier</label>
              <input
                type="text"
                value={llm.modelName}
                onChange={(e) => updateLLM({ modelName: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">API Key / Auth Token</label>
              <input
                type="password"
                value={llm.apiKey}
                onChange={(e) => updateLLM({ apiKey: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">FastAPI Endpoint Base URL</label>
              <input
                type="text"
                value={llm.baseUrl}
                onChange={(e) => updateLLM({ baseUrl: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* User Preferences & Appearance */}
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
            <Sliders className="w-4 h-4 text-purple-400" /> UI &amp; Code Editor Preferences
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">Theme</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={toggleTheme}
                  className={`flex-1 py-2 rounded-xl border flex items-center justify-center gap-2 font-medium transition-all ${
                    theme === 'dark'
                      ? 'bg-indigo-600 text-white border-indigo-500 shadow-glow'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  <Moon className="w-4 h-4 text-indigo-300" /> Dark Glass (Default)
                </button>
                <button
                  type="button"
                  onClick={toggleTheme}
                  className={`flex-1 py-2 rounded-xl border flex items-center justify-center gap-2 font-medium transition-all ${
                    theme === 'light'
                      ? 'bg-indigo-600 text-white border-indigo-500 shadow-glow'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  <Sun className="w-4 h-4 text-amber-400" /> Light Mode
                </button>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-slate-300 font-medium">Preferred Primary Language</label>
              <input
                type="text"
                value={preferences.preferredLanguage}
                onChange={(e) => updatePreferences({ preferredLanguage: e.target.value })}
                className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium text-sm shadow-glow flex items-center gap-2 transition-all"
          >
            <Save className="w-4 h-4" /> Save Settings
          </button>
        </div>
      </form>

      {/* GitHub Integration — outside the form so it submits separately */}
      <GitHubIntegrationPanel />
    </div>
  );
};
