import React, { useEffect, useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { Workspace } from '../../api/workspaces';
import {
  Plus, Search, FolderOpen, Calendar, Cpu, GitBranch, ChevronUp, ChevronDown,
  ChevronsUpDown, Loader2, AlertCircle, Trash2, Settings, Layers, ArrowUpDown
} from 'lucide-react';

const formatDate = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

type SortKey = 'name' | 'created_at' | 'updated_at' | 'repo_count';
type SortDir = 'asc' | 'desc';

const ITEMS_PER_PAGE = 9;

const WorkspaceCard: React.FC<{
  workspace: Workspace;
  isActive: boolean;
  onActivate: (id: string) => void;
  onDelete: (id: string, name: string) => void;
}> = ({ workspace, isActive, onActivate, onDelete }) => {
  const navigate = useNavigate();
  return (
    <div
      className={`relative group bg-[#0f141f] border rounded-2xl p-6 flex flex-col gap-4 transition-all duration-200 hover:shadow-xl hover:shadow-indigo-500/10 ${
        isActive
          ? 'border-indigo-500/60 shadow-lg shadow-indigo-500/20'
          : 'border-slate-800/80 hover:border-slate-700'
      }`}
    >
      {isActive && (
        <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
          Active
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3 pr-16">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/20">
          <Layers className="w-5 h-5 text-white" />
        </div>
        <div className="min-w-0">
          <h3 className="text-white font-semibold text-base truncate">{workspace.name}</h3>
          <p className="text-slate-500 text-xs mt-0.5 truncate">{workspace.description || 'No description'}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-900/60 rounded-lg p-2.5 flex items-center gap-2">
          <GitBranch className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          <span className="text-xs text-slate-300">{workspace.repo_count} repo{workspace.repo_count !== 1 ? 's' : ''}</span>
        </div>
        <div className="bg-slate-900/60 rounded-lg p-2.5 flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-purple-400 shrink-0" />
          <span className="text-xs text-slate-300 truncate">{workspace.default_ai_model}</span>
        </div>
      </div>

      {/* Dates */}
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <Calendar className="w-3 h-3" />
        <span>Created {formatDate(workspace.created_at)}</span>
        <span className="text-slate-700">·</span>
        <span>Updated {formatDate(workspace.updated_at)}</span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2 border-t border-slate-800/60">
        {!isActive && (
          <button
            onClick={() => onActivate(workspace.id)}
            className="flex-1 px-3 py-1.5 text-xs font-medium text-indigo-400 hover:text-white bg-indigo-500/10 hover:bg-indigo-600 border border-indigo-500/30 hover:border-indigo-500 rounded-lg transition-all"
          >
            Set Active
          </button>
        )}
        <button
          onClick={() => navigate(`/workspaces/${workspace.id}/settings`)}
          className="flex-1 px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-700 border border-slate-700/60 hover:border-slate-600 rounded-lg transition-all flex items-center justify-center gap-1.5"
        >
          <Settings className="w-3.5 h-3.5" /> Settings
        </button>
        <button
          onClick={() => onDelete(workspace.id, workspace.name)}
          className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

export const WorkspaceListPage: React.FC = () => {
  const { workspaces, isLoading, error, fetchWorkspaces, deleteWorkspace, setActiveWorkspace, activeWorkspaceId } = useWorkspaceStore();
  const _navigate = useNavigate();

  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('updated_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(1);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => { fetchWorkspaces(); }, [fetchWorkspaces]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const filtered = useMemo(() => {
    let result = [...workspaces];
    if (search) result = result.filter(w => w.name.toLowerCase().includes(search.toLowerCase()) || (w.description || '').toLowerCase().includes(search.toLowerCase()));
    result.sort((a, b) => {
      const va = a[sortKey] ?? '';
      const vb = b[sortKey] ?? '';
      const cmp = typeof va === 'number' ? va - (vb as number) : String(va).localeCompare(String(vb));
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return result;
  }, [workspaces, search, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const paginated = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await deleteWorkspace(deleteTarget.id);
    } finally {
      setIsDeleting(false);
      setDeleteTarget(null);
    }
  };

  const SortIcon = ({ k }: { k: SortKey }) => {
    if (sortKey !== k) return <ChevronsUpDown className="w-3.5 h-3.5 text-slate-600" />;
    return sortDir === 'asc'
      ? <ChevronUp className="w-3.5 h-3.5 text-indigo-400" />
      : <ChevronDown className="w-3.5 h-3.5 text-indigo-400" />;
  };

  return (
    <div className="p-8 max-w-7xl mx-auto w-full h-full overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Layers className="w-7 h-7 text-indigo-400" />
            Workspaces
          </h1>
          <p className="text-slate-400 mt-1">Manage your isolated engineering environments.</p>
        </div>
        <Link
          to="/workspaces/new"
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl transition-all shadow-lg shadow-indigo-500/25"
        >
          <Plus className="w-4 h-4" />
          New Workspace
        </Link>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search workspaces..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="w-full pl-10 pr-4 py-2.5 bg-slate-900/80 border border-slate-700/80 rounded-xl text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
          />
        </div>
        <div className="flex items-center gap-1.5 bg-slate-900/80 border border-slate-700/80 rounded-xl px-3 py-2">
          <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-xs text-slate-500 mr-1">Sort:</span>
          {(['name', 'created_at', 'updated_at', 'repo_count'] as SortKey[]).map(k => (
            <button
              key={k}
              onClick={() => handleSort(k)}
              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-colors ${sortKey === k ? 'bg-indigo-500/20 text-indigo-300' : 'text-slate-500 hover:text-slate-300'}`}
            >
              {{ name: 'Name', created_at: 'Created', updated_at: 'Updated', repo_count: 'Repos' }[k]}
              <SortIcon k={k} />
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading && workspaces.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mb-4" />
          <p className="text-slate-400">Loading workspaces...</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-32 text-center">
          <AlertCircle className="w-10 h-10 text-red-400 mb-4" />
          <p className="text-red-400 font-medium mb-2">Failed to load workspaces</p>
          <p className="text-slate-500 text-sm max-w-md mb-6">{error}</p>
          <button onClick={fetchWorkspaces} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors">
            Try Again
          </button>
        </div>
      ) : paginated.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-32 text-center">
          <div className="w-20 h-20 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-6">
            <FolderOpen className="w-10 h-10 text-indigo-400" />
          </div>
          <h3 className="text-white font-semibold text-lg mb-2">
            {search ? 'No workspaces found' : 'No workspaces yet'}
          </h3>
          <p className="text-slate-400 text-sm max-w-sm mb-8">
            {search ? `No results for "${search}". Try a different search term.` : 'Create your first workspace to start organizing your engineering environments.'}
          </p>
          {!search && (
            <Link to="/workspaces/new" className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl transition-all">
              <Plus className="w-4 h-4" /> Create Workspace
            </Link>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {paginated.map(ws => (
              <WorkspaceCard
                key={ws.id}
                workspace={ws}
                isActive={ws.id === activeWorkspaceId}
                onActivate={setActiveWorkspace}
                onDelete={(id, name) => setDeleteTarget({ id, name })}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm disabled:opacity-40 transition-colors">Prev</button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
                <button key={p} onClick={() => setPage(p)} className={`w-8 h-8 rounded-lg text-sm transition-colors ${p === page ? 'bg-indigo-600 text-white' : 'bg-slate-800 hover:bg-slate-700 text-slate-400'}`}>{p}</button>
              ))}
              <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)} className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm disabled:opacity-40 transition-colors">Next</button>
            </div>
          )}
        </>
      )}

      {/* Delete Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#0f172a] border border-slate-700/80 rounded-2xl p-6 max-w-sm w-full shadow-2xl">
            <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-4">
              <Trash2 className="w-6 h-6 text-red-400" />
            </div>
            <h3 className="text-white font-semibold text-lg mb-2">Delete Workspace</h3>
            <p className="text-slate-400 text-sm mb-6">
              Are you sure you want to delete <span className="text-white font-medium">"{deleteTarget.name}"</span>? All repositories inside will be removed. This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteTarget(null)} className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm rounded-xl transition-colors">
                Cancel
              </button>
              <button onClick={handleDelete} disabled={isDeleting} className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-70">
                {isDeleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
