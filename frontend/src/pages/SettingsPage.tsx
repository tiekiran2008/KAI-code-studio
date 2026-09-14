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
  Sparkles,
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
import { useTheme } from '../components/providers/ThemeProvider';

// ─── GitHub Integration Panel ─────────────────────────────────────────────────

const GitHubIntegrationPanel: React.FC = () => {
  const {
    status,
    isStatusLoading,
    statusError,
    isExpired,
    isConnecting,
    isDisconnecting,
    fetchStatus,
    startOAuthFlow,
    disconnect,
  } = useGitHubStore();
  const { addToast } = useUIStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const [showDisconnectConfirm, setShowDisconnectConfirm] = React.useState(false);

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

  const handleConfirmDisconnect = async () => {
    await disconnect();
    setShowDisconnectConfirm(false);
    addToast('GitHub account disconnected.', 'success');
  };

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      <h2 className="text-base font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
        <Github className="w-4 h-4 text-slate-300" /> GitHub Integration
      </h2>

      {/* Expired Token Alert */}
      {isExpired && (
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs space-y-2">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-amber-200">Your GitHub connection has expired.</p>
              <p className="text-[11px] text-amber-300/80 mt-0.5">
                Your authorization token is no longer valid or was revoked on GitHub. Please reconnect GitHub to restore full integration features.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              onClick={startOAuthFlow}
              className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all shadow-glow"
            >
              <Github className="w-3.5 h-3.5" /> Reconnect GitHub
            </button>
            <button
              type="button"
              onClick={() => setShowDisconnectConfirm(true)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
            >
              Disconnect
            </button>
          </div>
        </div>
      )}

      {statusError && !isExpired && (
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

          {showDisconnectConfirm ? (
            <div className="p-4 rounded-xl bg-slate-900 border border-rose-500/40 text-xs space-y-3 animate-in fade-in">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-white">Disconnect GitHub account?</p>
                  <p className="text-slate-400 text-[11px] mt-0.5">
                    This will safely remove your stored GitHub access token and connection metadata. Your existing imported repositories and projects will not be deleted.
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowDisconnectConfirm(false)}
                  disabled={isDisconnecting}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmDisconnect}
                  disabled={isDisconnecting}
                  className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-glow disabled:opacity-50"
                >
                  {isDisconnecting ? (
                    <><Loader2 className="w-3 h-3 animate-spin" /> Disconnecting…</>
                  ) : (
                    <><Link2Off className="w-3 h-3" /> Confirm Disconnect</>
                  )}
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowDisconnectConfirm(true)}
              disabled={isDisconnecting}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-950/30 border border-rose-500/30 hover:bg-rose-950/60 text-rose-400 text-xs font-semibold transition-all disabled:opacity-60"
            >
              <Link2Off className="w-3.5 h-3.5" /> Disconnect GitHub Account
            </button>
          )}
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
  const { addToast } = useUIStore();
  const {
    theme,
    setTheme,
    ambientIntensity,
    setAmbientIntensity,
    focusSession,
    setFocusSession,
    reduceMotion,
    setReduceMotion,
  } = useTheme();

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
        <div className="glass-panel p-6 rounded-2xl space-y-5">
          <h2 className="text-base font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
            <Sliders className="w-4 h-4 text-purple-400" /> UI &amp; Code Editor Preferences
          </h2>

          <div className="space-y-4 text-xs">
            <div className="space-y-2">
              <label className="text-slate-300 font-medium">Theme Selection</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
                {/* Dark Glass */}
                <button
                  type="button"
                  onClick={() => setTheme('dark')}
                  className={`p-3.5 rounded-xl border flex flex-col items-start gap-1.5 transition-all text-left min-w-0 ${
                    theme === 'dark'
                      ? 'bg-indigo-600/20 text-white border-indigo-500 shadow-glow'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2 font-medium">
                    <Moon className="w-4 h-4 text-indigo-400 shrink-0" /> Dark Glass
                  </div>
                  <span className="text-[11px] text-slate-400 leading-normal">Default dark developer environment</span>
                </button>

                {/* Light Mode */}
                <button
                  type="button"
                  onClick={() => setTheme('light')}
                  className={`p-3.5 rounded-xl border flex flex-col items-start gap-1.5 transition-all text-left min-w-0 ${
                    theme === 'light'
                      ? 'bg-indigo-600/20 text-white border-indigo-500 shadow-glow'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2 font-medium">
                    <Sun className="w-4 h-4 text-amber-400 shrink-0" /> Light Mode
                  </div>
                  <span className="text-[11px] text-slate-400 leading-normal">High-contrast daylight theme</span>
                </button>

                {/* Ambient Focus */}
                <button
                  type="button"
                  onClick={() => setTheme('ambient')}
                  className={`p-3.5 rounded-xl border flex flex-col items-start gap-1.5 transition-all text-left min-w-0 sm:col-span-2 lg:col-span-1 ${
                    theme === 'ambient'
                      ? 'bg-gradient-to-br from-indigo-950/80 to-purple-950/80 text-cyan-200 border-cyan-500/50 shadow-glow'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center gap-2 font-medium flex-wrap">
                    <Sparkles className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Ambient Focus</span>
                    <span className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[9px] font-semibold uppercase tracking-wider shrink-0">
                      Signature
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400 leading-normal">Atmospheric depth &amp; active focus auras</span>
                </button>
              </div>
            </div>

            {/* Ambient Focus Customization Panel */}
            {theme === 'ambient' && (
              <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/20 space-y-4 animate-in fade-in duration-200">
                <div className="flex items-center justify-between border-b border-indigo-500/20 pb-2">
                  <div className="flex items-center gap-2 text-indigo-300 font-semibold">
                    <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> Ambient Focus Customization
                  </div>
                  <span className="text-[11px] text-slate-400">GPU-accelerated atmospheric layers</span>
                </div>

                {/* Ambient Intensity */}
                <div className="space-y-1.5">
                  <label className="text-slate-300 font-medium">Atmospheric Intensity</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['minimal', 'balanced', 'immersive'] as const).map((level) => (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setAmbientIntensity(level)}
                        className={`py-1.5 px-3 rounded-lg border text-xs capitalize transition-all ${
                          ambientIntensity === level
                            ? 'bg-indigo-600 text-white border-indigo-400 shadow-glow'
                            : 'bg-slate-900/80 text-slate-400 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        {level}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Focus Session Mode Toggle */}
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <div className="text-slate-200 font-medium">Focus Session Mode</div>
                    <div className="text-[11px] text-slate-400">
                      Dims secondary navigation and maximizes visual prominence on your active workspace
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setFocusSession(!focusSession)}
                    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      focusSession ? 'bg-indigo-600' : 'bg-slate-800'
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                        focusSession ? 'translate-x-4' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>

                {/* Reduce Motion Toggle */}
                <div className="flex items-center justify-between pt-1">
                  <div>
                    <div className="text-slate-200 font-medium">Reduce Motion</div>
                    <div className="text-[11px] text-slate-400">
                      Pauses ambient color field movement while preserving full static atmospheric depth
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setReduceMotion(!reduceMotion)}
                    className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                      reduceMotion ? 'bg-indigo-600' : 'bg-slate-800'
                    }`}
                  >
                    <span
                      className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                        reduceMotion ? 'translate-x-4' : 'translate-x-0'
                      }`}
                    />
                  </button>
                </div>
              </div>
            )}

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
