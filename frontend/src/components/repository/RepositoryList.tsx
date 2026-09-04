import React, { useState } from 'react';
import { 
  GitBranch, 
  Search, 
  RefreshCw, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  Trash2, 
  ExternalLink,
  Eye
} from 'lucide-react';
import { Repository } from '../../types';
import { useRepoStore } from '../../store/useRepoStore';

interface RepositoryListProps {
  repositories: Repository[];
  onInspect: (repo: Repository) => void;
  onDelete: (repo: Repository) => void;
  onReindex: (repoId: string) => void;
}

export const RepositoryList: React.FC<RepositoryListProps> = ({
  repositories,
  onInspect,
  onDelete,
  onReindex,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const { setSelectedBranch } = useRepoStore();

  const filteredRepos = repositories.filter(
    (repo) =>
      repo.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      repo.language.toLowerCase().includes(searchTerm.toLowerCase()) ||
      repo.owner.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search repositories..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="text-xs text-slate-400">
          Showing <span className="font-semibold text-slate-200">{filteredRepos.length}</span> of{' '}
          <span className="font-semibold text-slate-200">{repositories.length}</span> repositories
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">Repository Name</th>
              <th className="px-4 py-3">Language</th>
              <th className="px-4 py-3">Active Branch</th>
              <th className="px-4 py-3">Indexed Chunks</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last Indexed</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredRepos.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-slate-400 text-xs">
                  No repositories match your search query.
                </td>
              </tr>
            ) : (
              filteredRepos.map((repo) => (
                <tr key={repo.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="px-4 py-4 font-semibold text-slate-100 flex items-center gap-2">
                    <GitBranch className="w-4 h-4 text-indigo-400 shrink-0" />
                    <div>
                      <div className="flex items-center gap-1.5">
                        {repo.name}
                        {repo.url && repo.url.startsWith('http') && (
                          <a
                            href={repo.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-slate-500 hover:text-indigo-400"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500 font-normal">{repo.owner}</div>
                    </div>
                  </td>

                  <td className="px-4 py-4 text-xs font-mono">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {repo.language}
                    </span>
                  </td>

                  <td className="px-4 py-4 text-xs font-mono">
                    <select
                      value={repo.currentBranch}
                      onChange={(e) => setSelectedBranch(e.target.value)}
                      className="bg-slate-900 border border-slate-700 text-indigo-300 px-2.5 py-1 rounded-lg focus:outline-none focus:border-indigo-500"
                    >
                      {repo.branches.map((b) => (
                        <option key={b} value={b}>
                          {b}
                        </option>
                      ))}
                    </select>
                  </td>

                  <td className="px-4 py-4 text-xs font-mono">{repo.chunksCount} chunks</td>

                  <td className="px-4 py-4">
                    {repo.indexingStatus === 'indexed' && (
                      <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Indexed
                      </span>
                    )}
                    {repo.indexingStatus === 'indexing' && (
                      <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium animate-pulse">
                        <Clock className="w-3.5 h-3.5" /> Indexing...
                      </span>
                    )}
                    {repo.indexingStatus === 'failed' && (
                      <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 font-medium">
                        <AlertCircle className="w-3.5 h-3.5" /> Failed
                      </span>
                    )}
                    {repo.indexingStatus === 'pending' && (
                      <span className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-slate-500/10 text-slate-400 border border-slate-500/20 font-medium">
                        <Clock className="w-3.5 h-3.5" /> Pending
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-4 text-xs text-slate-400">
                    {new Date(repo.lastIndexedAt).toLocaleDateString()}
                  </td>

                  <td className="px-4 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onReindex(repo.id)}
                        className="p-1.5 rounded-lg glass-button text-slate-400 hover:text-white"
                        title="Re-index repository"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => onInspect(repo)}
                        className="px-3 py-1.5 rounded-lg bg-indigo-600/30 text-indigo-300 hover:bg-indigo-600/50 text-xs font-medium border border-indigo-500/30 flex items-center gap-1"
                      >
                        <Eye className="w-3.5 h-3.5" /> Inspect
                      </button>
                      <button
                        onClick={() => onDelete(repo)}
                        className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 text-xs font-medium"
                        title="Delete repository"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
