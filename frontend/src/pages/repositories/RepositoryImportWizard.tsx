import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRepositoryStore } from '../../store/repositoryStore';
import { useGitHubStore } from '../../store/useGitHubStore';
import { GitHubRepository } from '../../api/integrations';
import { RepositoryProvider } from '../../types';
import {
  Github, GitBranch, HardDrive, ArrowLeft, CheckCircle2,
  RefreshCw, Lock, Sparkles, AlertCircle, Layers, FileCode,
  Database, ArrowRight, Search, Star,
  Link2Off, Loader2, ChevronDown,
} from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { RepositoryIndexStatus } from '../../api/repositories';

// ─── Sub-component: GitHub Repository Picker ─────────────────────────────────

interface GitHubPickerProps {
  onSelect: (repo: GitHubRepository) => void;
  onConnectRequest: () => void;
}

const GitHubRepoPicker: React.FC<GitHubPickerProps> = ({ onSelect, onConnectRequest }) => {
  const {
    status, isStatusLoading, fetchStatus,
    repositories, isReposLoading, reposError, hasMore,
    fetchRepositories, loadMoreRepositories, setReposSearch, resetRepos,
  } = useGitHubStore();

  const [search, setSearch] = useState('');
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (status?.connected) {
      resetRepos();
      fetchRepositories({ page: 1, search: '' });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status?.connected]);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value;
      setSearch(val);
      setReposSearch(val);
      if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
      searchTimerRef.current = setTimeout(() => {
        fetchRepositories({ page: 1, search: val });
      }, 400);
    },
    [fetchRepositories, setReposSearch],
  );

  if (isStatusLoading) {
    return (
      <div className="flex items-center justify-center py-10 text-slate-400">
        <Loader2 className="w-5 h-5 animate-spin mr-2" /> Checking GitHub connection…
      </div>
    );
  }

  if (!status?.connected) {
    return (
      <div className="flex flex-col items-center gap-4 py-10 text-center">
        <div className="p-4 rounded-2xl bg-slate-800 text-indigo-400">
          <Github className="w-8 h-8" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white mb-1">GitHub Not Connected</p>
          <p className="text-xs text-slate-400 max-w-xs">
            Connect your GitHub account to browse and import private and public repositories directly.
          </p>
        </div>
        <button
          type="button"
          onClick={onConnectRequest}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold flex items-center gap-2 shadow-glow transition-all"
        >
          <Github className="w-4 h-4" /> Connect GitHub Account
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Connected badge */}
      <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/20">
        {status.avatar_url && (
          <img src={status.avatar_url} alt={status.username || ''} className="w-7 h-7 rounded-full" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" /> Connected as <span className="font-mono">{status.username}</span>
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
        <input
          type="text"
          placeholder="Search your repositories…"
          value={search}
          onChange={handleSearchChange}
          className="w-full pl-8 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 font-mono"
        />
      </div>

      {/* Repo list */}
      {reposError && (
        <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" /> {reposError}
        </div>
      )}

      <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
        {isReposLoading && repositories.length === 0 && (
          <div className="flex items-center justify-center py-8 text-slate-400 text-xs">
            <Loader2 className="w-4 h-4 animate-spin mr-2" /> Loading repositories…
          </div>
        )}
        {!isReposLoading && repositories.length === 0 && (
          <div className="py-8 text-center text-slate-500 text-xs">
            No repositories found{search ? ` for "${search}"` : ''}.
          </div>
        )}
        {repositories.map((repo) => (
          <button
            key={repo.id}
            type="button"
            onClick={() => onSelect(repo)}
            className="w-full text-left p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/70 transition-all group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-xs font-semibold text-white font-mono truncate group-hover:text-indigo-300 transition-colors">
                  {repo.full_name}
                </p>
                {repo.description && (
                  <p className="text-[11px] text-slate-500 truncate mt-0.5">{repo.description}</p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0 mt-0.5">
                {repo.is_private && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950/50 text-amber-400 border border-amber-900/50 font-medium">
                    Private
                  </span>
                )}
                {repo.language && (
                  <span className="text-[10px] text-slate-500 font-mono">{repo.language}</span>
                )}
                {repo.stars > 0 && (
                  <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                    <Star className="w-3 h-3" /> {repo.stars}
                  </span>
                )}
              </div>
            </div>
          </button>
        ))}
        {hasMore && repositories.length > 0 && (
          <button
            type="button"
            onClick={loadMoreRepositories}
            disabled={isReposLoading}
            className="w-full py-2 text-center text-xs text-slate-400 hover:text-white transition-colors flex items-center justify-center gap-1 disabled:opacity-50"
          >
            {isReposLoading ? (
              <><Loader2 className="w-3 h-3 animate-spin" /> Loading…</>
            ) : (
              <><ChevronDown className="w-3 h-3" /> Load more</>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

// ─── Main Wizard Component ────────────────────────────────────────────────────

export const RepositoryImportWizard: React.FC = () => {
  const navigate = useNavigate();
  const { importRepository, fetchIndexStatus, isImporting, error } = useRepositoryStore();
  const { workspaces, activeWorkspaceId } = useWorkspaceStore();
  const { startOAuthFlow, isConnecting } = useGitHubStore();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [provider, setProvider] = useState<RepositoryProvider>('github');
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [branch, setBranch] = useState('main');
  const [token, setToken] = useState('');
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(activeWorkspaceId || '');
  const [validationErr, setValidationErr] = useState('');

  // GitHub OAuth picker sub-state
  const [useGitHubPicker, setUseGitHubPicker] = useState(false);

  // Step 3 Live Indexing State
  const [importedRepoId, setImportedRepoId] = useState<string | null>(null);
  const [indexProgress, setIndexProgress] = useState<RepositoryIndexStatus | null>(null);
  const pollTimerRef = useRef<any>(null);

  const handleProviderSelect = (p: RepositoryProvider) => {
    setProvider(p);
    setUseGitHubPicker(p === 'github');
    setStep(2);
  };

  /** Called when user picks a repo from the GitHub picker */
  const handleGitHubRepoSelect = (repo: GitHubRepository) => {
    setUrl(repo.clone_url);
    setName(repo.name);
    setDescription(repo.description || '');
    setBranch(repo.default_branch);
    setUseGitHubPicker(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) {
      setValidationErr('Repository URL or local path is required');
      return;
    }
    setValidationErr('');

    try {
      const newRepo = await importRepository({
        url: url.trim(),
        provider,
        name: name.trim() || undefined,
        description: description.trim() || undefined,
        default_branch: branch.trim() || 'main',
        workspace_id: selectedWorkspaceId || undefined,
        git_access_token: token.trim() || undefined,
      });

      setImportedRepoId(newRepo.id);
      setStep(3);
    } catch (err: any) {
      setValidationErr(err.message || 'Failed to import repository.');
    }
  };

  // Poll indexing status when in step 3
  useEffect(() => {
    if (step === 3 && importedRepoId) {
      const poll = async () => {
        try {
          const status = await fetchIndexStatus(importedRepoId);
          setIndexProgress(status);
          if (status.status === 'indexed' || status.status === 'completed' || status.status === 'failed') {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          }
        } catch {
          // ignore poll error and retry
        }
      };

      poll();
      pollTimerRef.current = setInterval(poll, 1500);

      return () => {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      };
    }
  }, [step, importedRepoId, fetchIndexStatus]);

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => {
            if (step === 2) {
              setStep(1);
              setUseGitHubPicker(false);
            } else {
              navigate('/repositories');
            }
          }}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> {step === 2 ? 'Back to Provider Selection' : 'Back to Dashboard'}
        </button>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          Step <span className="text-indigo-400 font-bold">{step}</span> of 3
        </div>
      </div>

      <div className="glass-panel p-8 rounded-2xl space-y-6 border border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            {step === 3 ? 'Repository Indexing in Progress' : 'Import Repository'}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {step === 3
              ? 'Our multi-agent AST parser and embedding engine is processing your codebase into Qdrant vector memory.'
              : 'Connect your codebase from GitHub, GitLab, Bitbucket, or a local directory to run AI stack analysis and indexing.'}
          </p>
        </div>

        {/* Step 1: Provider Select */}
        {step === 1 && (
          <div className="space-y-4">
            <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Select Repository Source
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => handleProviderSelect('github')}
                className={`p-5 rounded-2xl border text-left flex items-start gap-4 transition-all ${
                  provider === 'github'
                    ? 'bg-indigo-950/40 border-indigo-500 shadow-glow'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="p-3 rounded-xl bg-slate-800 text-indigo-400 shrink-0">
                  <Github className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">GitHub</h3>
                  <p className="text-xs text-slate-400 mt-1">Public or private GitHub repository via OAuth or HTTPS</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleProviderSelect('gitlab')}
                className={`p-5 rounded-2xl border text-left flex items-start gap-4 transition-all ${
                  provider === 'gitlab'
                    ? 'bg-orange-950/40 border-orange-500 shadow-glow'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="p-3 rounded-xl bg-slate-800 text-orange-400 shrink-0">
                  <GitBranch className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">GitLab</h3>
                  <p className="text-xs text-slate-400 mt-1">GitLab.com or self-hosted GitLab instance</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleProviderSelect('bitbucket')}
                className={`p-5 rounded-2xl border text-left flex items-start gap-4 transition-all ${
                  provider === 'bitbucket'
                    ? 'bg-blue-950/40 border-blue-500 shadow-glow'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="p-3 rounded-xl bg-slate-800 text-blue-400 shrink-0">
                  <GitBranch className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Bitbucket</h3>
                  <p className="text-xs text-slate-400 mt-1">Bitbucket Cloud or Server repository</p>
                </div>
              </button>

              <button
                type="button"
                onClick={() => handleProviderSelect('local')}
                className={`p-5 rounded-2xl border text-left flex items-start gap-4 transition-all ${
                  provider === 'local'
                    ? 'bg-purple-950/40 border-purple-500 shadow-glow'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="p-3 rounded-xl bg-slate-800 text-purple-400 shrink-0">
                  <HardDrive className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Local Directory</h3>
                  <p className="text-xs text-slate-400 mt-1">Index code directly from local file-system path</p>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Step 2: GitHub Picker or Manual Form */}
        {step === 2 && provider === 'github' && useGitHubPicker && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Select a GitHub Repository
              </label>
              <button
                type="button"
                onClick={() => setUseGitHubPicker(false)}
                className="text-xs text-slate-400 hover:text-indigo-300 transition-colors flex items-center gap-1"
              >
                <Link2Off className="w-3.5 h-3.5" /> Enter URL manually
              </button>
            </div>
            <GitHubRepoPicker
              onSelect={handleGitHubRepoSelect}
              onConnectRequest={startOAuthFlow}
            />
          </div>
        )}

        {/* Step 2: Manual form (all providers, or GitHub after picker selection) */}
        {step === 2 && (!useGitHubPicker || provider !== 'github') && (
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* GitHub: switch to picker */}
            {provider === 'github' && (
              <button
                type="button"
                onClick={() => setUseGitHubPicker(true)}
                disabled={isConnecting}
                className="w-full py-2.5 rounded-xl border border-indigo-500/40 bg-indigo-950/20 hover:bg-indigo-950/40 text-indigo-300 text-xs font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-60"
              >
                {isConnecting ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Connecting…</>
                ) : (
                  <><Github className="w-3.5 h-3.5" /> Browse GitHub Repositories</>
                )}
              </button>
            )}

            {(validationErr || error) && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {validationErr || error}
              </div>
            )}

            {/* Show auto-filled values when selected from picker */}
            {url && provider === 'github' && (
              <div className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/20 text-xs flex items-center gap-2 text-indigo-300">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                <span className="font-mono truncate">{url}</span>
                <button
                  type="button"
                  onClick={() => setUseGitHubPicker(true)}
                  className="ml-auto text-slate-400 hover:text-white shrink-0"
                >
                  Change
                </button>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">
                {provider === 'local' ? 'Local Directory Absolute Path' : 'Repository URL'}
              </label>
              <input
                type="text"
                required
                placeholder={
                  provider === 'local'
                    ? 'd:/Software Engineering AI Agent/backend'
                    : `https://${provider}.com/owner/repository`
                }
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Repository Name (Optional)</label>
                <input
                  type="text"
                  placeholder="Auto-detected from URL if left empty"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300">Default Branch</label>
                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300">Target Workspace</label>
              <select
                value={selectedWorkspaceId}
                onChange={(e) => setSelectedWorkspaceId(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="">No Workspace (Global)</option>
                {workspaces.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </div>

            {provider !== 'local' && provider !== 'github' && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-indigo-400" /> Access Token (Personal Access Token for Private Repos)
                </label>
                <input
                  type="password"
                  placeholder="glpat-•••••••••••• or app-token"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-slate-500">Stored encrypted server-side; used solely for pulling repository context.</p>
              </div>
            )}

            {provider === 'github' && !url && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <Lock className="w-3.5 h-3.5 text-indigo-400" /> Personal Access Token (for private repos without OAuth)
                </label>
                <input
                  type="password"
                  placeholder="ghp_••••••••••••"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-slate-500">Stored encrypted server-side; used solely for pulling repository context.</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isImporting}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm shadow-glow flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              {isImporting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Starting Ingestion...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" /> Confirm &amp; Start Indexing
                </>
              )}
            </button>
          </form>
        )}

        {/* Step 3: Live Progress */}
        {step === 3 && (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Progress Bar Container */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-300 flex items-center gap-2 capitalize">
                  {indexProgress?.status === 'indexed' || indexProgress?.status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : indexProgress?.status === 'failed' ? (
                    <AlertCircle className="w-4 h-4 text-rose-400" />
                  ) : (
                    <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin" />
                  )}
                  Stage: <span className="text-white font-mono">{indexProgress?.stage || 'cloning'}</span>
                </span>
                <span className="font-mono text-indigo-400 font-bold">
                  {indexProgress?.progress ?? 5}%
                </span>
              </div>

              <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${
                    indexProgress?.status === 'failed'
                      ? 'bg-rose-500'
                      : indexProgress?.status === 'indexed' || indexProgress?.status === 'completed'
                      ? 'bg-emerald-500 shadow-glow'
                      : 'bg-gradient-to-r from-indigo-500 to-purple-500'
                  }`}
                  style={{ width: `${Math.max(5, indexProgress?.progress ?? 5)}%` }}
                />
              </div>
            </div>

            {/* Metrics cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-indigo-950/50 text-indigo-400">
                  <FileCode className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] text-slate-400">Discovered Files</div>
                  <div className="text-base font-bold text-white font-mono">
                    {indexProgress?.files_discovered ?? 0}
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-purple-950/50 text-purple-400">
                  <Layers className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] text-slate-400">Processed Files</div>
                  <div className="text-base font-bold text-white font-mono">
                    {indexProgress?.files_processed ?? 0}
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-emerald-950/50 text-emerald-400">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-[11px] text-slate-400">Qdrant Chunks</div>
                  <div className="text-base font-bold text-white font-mono">
                    {indexProgress?.chunks_created ?? 0}
                  </div>
                </div>
              </div>
            </div>

            {indexProgress?.error && (
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                Error: {indexProgress.error}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-4 pt-2">
              <button
                type="button"
                onClick={() => navigate('/repositories')}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors text-center"
              >
                View Repository Dashboard
              </button>
              {(indexProgress?.status === 'indexed' || indexProgress?.status === 'completed') && (
                <button
                  type="button"
                  onClick={() => navigate(`/repositories/${importedRepoId}`)}
                  className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-glow"
                >
                  Open Repository Details <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
