import React, { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRepositoryStore } from '../../store/repositoryStore';
import { useRepoStore } from '../../store/useRepoStore';
import { RepositoryProvider, IndexingStatus } from '../../types';
import {
  Search, Plus, GitBranch, RefreshCw, CheckCircle2, Clock, AlertCircle,
  Trash2, Eye, Filter, Github, ExternalLink, HardDrive, Loader2, XCircle, Code2
} from 'lucide-react';


const ProviderBadge: React.FC<{ provider?: RepositoryProvider }> = ({ provider = 'github' }) => {
  switch (provider) {
    case 'github':
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700 text-[11px] font-mono"><Github className="w-3 h-3" /> GitHub</span>;
    case 'gitlab':
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-orange-950/40 text-orange-400 border border-orange-800/40 text-[11px] font-mono">GitLab</span>;
    case 'bitbucket':
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-950/40 text-blue-400 border border-blue-800/40 text-[11px] font-mono">Bitbucket</span>;
    case 'local':
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-purple-950/40 text-purple-400 border border-purple-800/40 text-[11px] font-mono"><HardDrive className="w-3 h-3" /> Local</span>;
    default:
      return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px]">{provider}</span>;
  }
};

const StatusBadge: React.FC<{ status?: IndexingStatus }> = ({ status = 'indexed' }) => {
  switch (status) {
    case 'indexed':
      return <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3" /> Indexed</span>;
    case 'indexing':
      return <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"><Clock className="w-3 h-3" /> Indexing...</span>;
    case 'failed':
      return <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20"><AlertCircle className="w-3 h-3" /> Failed</span>;
    default:
      return <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700"><Clock className="w-3 h-3" /> Pending</span>;
  }
};

export const RepositoryDashboard: React.FC = () => {
  const navigate = useNavigate();
  const {
    repositories,
    isLoading,
    fetchRepositories,
    deleteRepository,
    reindexRepository,
    fetchIndexStatus,
  } = useRepositoryStore();
  const { setActiveRepo } = useRepoStore();


  const [search, setSearch] = useState('');
  const [providerFilter, setProviderFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'updated_at' | 'chunks'>('updated_at');

  // Per-repo reindex loading state: repoId -> true while the POST is in flight
  const [reindexingIds, setReindexingIds] = useState<Set<string>>(new Set());
  // Per-repo error messages surfaced from failed reindex requests
  const [reindexErrors, setReindexErrors] = useState<Record<string, string>>({});

  // Polling refs: track which repos are actively being indexed so we can poll
  const pollingRefs = useRef<Record<string, ReturnType<typeof setInterval>>>({});

  const stopPolling = useCallback((repoId: string) => {
    if (pollingRefs.current[repoId]) {
      clearInterval(pollingRefs.current[repoId]);
      delete pollingRefs.current[repoId];
    }
  }, []);

  const startPolling = useCallback((repoId: string) => {
    stopPolling(repoId);
    pollingRefs.current[repoId] = setInterval(async () => {
      try {
        const status = await fetchIndexStatus(repoId);
        if (status.status !== 'indexing') {
          stopPolling(repoId);
          // Refresh full list to sync chunks_count etc.
          fetchRepositories();
        }
      } catch {
        stopPolling(repoId);
      }
    }, 5000);
  }, [fetchIndexStatus, fetchRepositories, stopPolling]);

  // Clean up all polling on unmount
  useEffect(() => {
    return () => {
      Object.keys(pollingRefs.current).forEach(stopPolling);
    };
  }, [stopPolling]);

  const handleReindex = useCallback(async (repoId: string) => {
    setReindexingIds((prev) => new Set(prev).add(repoId));
    setReindexErrors((prev) => { const n = { ...prev }; delete n[repoId]; return n; });
    try {
      await reindexRepository(repoId);
      startPolling(repoId);
    } catch (err: any) {
      setReindexErrors((prev) => ({ ...prev, [repoId]: err.message || 'Failed to start re-indexing' }));
    } finally {
      setReindexingIds((prev) => { const n = new Set(prev); n.delete(repoId); return n; });
    }
  }, [reindexRepository, startPolling]);

  useEffect(() => {
    fetchRepositories();
  }, [fetchRepositories]);

  const filtered = useMemo(() => {
    return repositories.filter((repo) => {
      const matchSearch =
        repo.name.toLowerCase().includes(search.toLowerCase()) ||
        (repo.owner || '').toLowerCase().includes(search.toLowerCase()) ||
        (repo.detected_stack?.language || repo.language || '').toLowerCase().includes(search.toLowerCase());
      const matchProvider = providerFilter === 'all' || repo.provider === providerFilter;
      const matchStatus = statusFilter === 'all' || (repo.indexing_status || repo.indexingStatus) === statusFilter;
      return matchSearch && matchProvider && matchStatus;
    }).sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'chunks') return (b.chunks_count || b.chunksCount || 0) - (a.chunks_count || a.chunksCount || 0);
      return new Date(b.updated_at || b.lastIndexedAt || 0).getTime() - new Date(a.updated_at || a.lastIndexedAt || 0).getTime();
    });
  }, [repositories, search, providerFilter, statusFilter, sortBy]);

  const stats = useMemo(() => {
    const total = repositories.length;
    const indexed = repositories.filter((r) => (r.indexing_status || r.indexingStatus) === 'indexed').length;
    const indexing = repositories.filter((r) => (r.indexing_status || r.indexingStatus) === 'indexing').length;
    const failed = repositories.filter((r) => (r.indexing_status || r.indexingStatus) === 'failed').length;
    const chunks = repositories.reduce((sum, r) => sum + (r.chunks_count || r.chunksCount || 0), 0);
    return { total, indexed, indexing, failed, chunks };
  }, [repositories]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-slate-800">
          <p className="text-xs text-slate-400 font-medium">Total Repositories</p>
          <p className="text-2xl font-bold text-white mt-1">{stats.total}</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-emerald-900/30">
          <p className="text-xs text-emerald-400 font-medium">Indexed & Ready</p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">{stats.indexed}</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-amber-900/30">
          <p className="text-xs text-amber-400 font-medium">Indexing in Progress</p>
          <p className="text-2xl font-bold text-amber-400 mt-1">{stats.indexing}</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-rose-900/30">
          <p className="text-xs text-rose-400 font-medium">Indexing Failures</p>
          <p className="text-2xl font-bold text-rose-400 mt-1">{stats.failed}</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-indigo-900/30">
          <p className="text-xs text-indigo-400 font-medium">Code Vector Chunks</p>
          <p className="text-2xl font-bold text-indigo-300 mt-1">{stats.chunks.toLocaleString()}</p>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto flex-1">
          <div className="relative flex-1 sm:w-64 min-w-[200px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by name, owner, stack..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={providerFilter}
              onChange={(e) => setProviderFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Providers</option>
              <option value="github">GitHub</option>
              <option value="gitlab">GitLab</option>
              <option value="bitbucket">Bitbucket</option>
              <option value="local">Local</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Statuses</option>
              <option value="indexed">Indexed</option>
              <option value="indexing">Indexing</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
            </select>

            <select
              value={sortBy}
              onChange={(e: any) => setSortBy(e.target.value)}
              className="bg-slate-900 border border-slate-800 text-slate-300 text-xs rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
            >
              <option value="updated_at">Recently Updated</option>
              <option value="name">Name (A-Z)</option>
              <option value="chunks">Most Chunks</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => navigate('/repositories/import')}
          className="w-full sm:w-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 shadow-glow transition-all"
        >
          <Plus className="w-4 h-4" /> Import Repository
        </button>
      </div>

      {/* Repositories Table */}
      <div className="glass-panel rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Repository</th>
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Detected AI Stack</th>
                <th className="px-4 py-3">Branch</th>
                <th className="px-4 py-3">Vector Chunks</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400 text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-indigo-400" />
                    Loading repository details...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400 text-xs">
                    No repositories found matching your search and filter criteria.
                  </td>
                </tr>
              ) : (
                filtered.map((repo) => {
                  const stack = repo.detected_stack;
                  const primaryLang = stack?.language || repo.language || 'Unknown';
                  const framework = stack?.framework;
                  const curBranch = repo.current_branch || repo.currentBranch || repo.default_branch || repo.defaultBranch || 'main';

                  return (
                    <tr key={repo.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="px-4 py-4 font-semibold text-slate-100 flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-indigo-950/60 border border-indigo-500/20 flex items-center justify-center shrink-0">
                          <GitBranch className="w-4 h-4 text-indigo-400" />
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span
                              onClick={() => navigate(`/repositories/${repo.id}`)}
                              className="hover:text-indigo-400 cursor-pointer transition-colors"
                            >
                              {repo.name}
                            </span>
                            {repo.url.startsWith('http') && (
                              <a href={repo.url} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-indigo-400">
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500 font-normal truncate max-w-xs">
                            {repo.description || repo.owner || repo.url}
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <ProviderBadge provider={repo.provider} />
                      </td>

                      <td className="px-4 py-4 text-xs">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-200 border border-slate-700 font-mono text-[11px]">
                            {primaryLang}
                          </span>
                          {framework && (
                            <span className="px-2 py-0.5 rounded bg-indigo-950/50 text-indigo-300 border border-indigo-800/40 font-mono text-[11px]">
                              {framework}
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-4 py-4 text-xs font-mono text-indigo-300">
                        {curBranch}
                      </td>

                      <td className="px-4 py-4 text-xs font-mono">
                        {(repo.chunks_count || repo.chunksCount || 0).toLocaleString()}
                      </td>

                      <td className="px-4 py-4">
                        <StatusBadge status={repo.indexing_status || repo.indexingStatus} />
                      </td>

                      <td className="px-4 py-4 text-right">
                        <div className="flex flex-col items-end gap-1">
                          <div className="flex items-center justify-end gap-2">
                            {/* Re-index button — calls POST /api/v1/repositories/{id}/reindex */}
                            <button
                              id={`reindex-btn-${repo.id}`}
                              onClick={() => handleReindex(repo.id)}
                              disabled={
                                reindexingIds.has(repo.id) ||
                                (repo.indexing_status || repo.indexingStatus) === 'indexing'
                              }
                              className="p-1.5 rounded-lg glass-button text-slate-400 hover:text-indigo-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                              title="Re-index repository (triggers full Qdrant ingestion)"
                            >
                              {reindexingIds.has(repo.id) ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <RefreshCw className="w-3.5 h-3.5" />
                              )}
                            </button>
                            <button
                              onClick={async () => {
                                await setActiveRepo(repo);
                                navigate('/workspace');
                              }}
                              className="px-3 py-1.5 rounded-lg bg-indigo-600/30 text-indigo-300 hover:bg-indigo-600/50 text-xs font-medium border border-indigo-500/30 flex items-center gap-1"
                              title="Open in AI Workspace"
                            >
                              <Code2 className="w-3.5 h-3.5" /> Workspace
                            </button>
                            <button
                              onClick={() => navigate(`/repositories/${repo.id}`)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 text-xs font-medium border border-slate-800"
                              title="Inspect repository details"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => deleteRepository(repo.id)}
                              className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-medium"
                              title="Delete repository"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>

                          </div>
                          {/* Inline error for this row */}
                          {reindexErrors[repo.id] && (
                            <div className="flex items-center gap-1 text-[10px] text-rose-400 max-w-[220px] text-right">
                              <XCircle className="w-3 h-3 shrink-0" />
                              <span className="truncate">{reindexErrors[repo.id]}</span>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
