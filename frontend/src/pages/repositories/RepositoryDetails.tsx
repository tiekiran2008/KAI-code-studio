import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useRepositoryStore } from '../../store/repositoryStore';
import { RepositoryIndexStatus } from '../../api/repositories';
import {
  GitBranch, ArrowLeft, RefreshCw, CheckCircle2, Clock, AlertCircle,
  Cpu, Trash2, Edit3, Check
} from 'lucide-react';

export const RepositoryDetails: React.FC = () => {
  const { repoId } = useParams<{ repoId: string }>();
  const navigate = useNavigate();
  const {
    selectedRepo,
    fetchRepository,
    updateRepository,
    reindexRepository,
    fetchIndexStatus,
    switchBranch,
    deleteRepository,
  } = useRepositoryStore();

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetBranch, setTargetBranch] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [liveIndexStatus, setLiveIndexStatus] = useState<RepositoryIndexStatus | null>(null);
  const pollRef = useRef<any>(null);

  useEffect(() => {
    if (repoId) {
      fetchRepository(repoId);
    }
  }, [repoId, fetchRepository]);

  useEffect(() => {
    if (selectedRepo) {
      setName(selectedRepo.name);
      setDescription(selectedRepo.description || '');
      setTargetBranch(selectedRepo.current_branch || selectedRepo.currentBranch || selectedRepo.default_branch || selectedRepo.defaultBranch || 'main');
    }
  }, [selectedRepo]);

  // Poll indexing status if indexing
  useEffect(() => {
    const isCurrentlyIndexing =
      selectedRepo?.indexing_status === 'indexing' || isReindexing;

    if (repoId && isCurrentlyIndexing) {
      const poll = async () => {
        try {
          const status = await fetchIndexStatus(repoId);
          setLiveIndexStatus(status);
          if (status.status === 'indexed' || status.status === 'completed' || status.status === 'failed') {
            setIsReindexing(false);
            if (pollRef.current) clearInterval(pollRef.current);
          }
        } catch {
          // ignore error
        }
      };

      poll();
      pollRef.current = setInterval(poll, 1500);

      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
  }, [repoId, selectedRepo?.indexing_status, isReindexing, fetchIndexStatus]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoId) return;
    setIsSaving(true);
    try {
      await updateRepository(repoId, { name, description });
      setEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleBranchSwitch = async (b: string) => {
    if (!repoId) return;
    await switchBranch(repoId, b);
    setTargetBranch(b);
  };

  const handleReindex = async () => {
    if (!repoId) return;
    setIsReindexing(true);
    try {
      await reindexRepository(repoId);
    } catch {
      setIsReindexing(false);
    }
  };

  const handleDelete = async () => {
    if (!repoId) return;
    if (window.confirm(`Are you sure you want to delete ${selectedRepo?.name}?`)) {
      await deleteRepository(repoId);
      navigate('/repositories');
    }
  };

  if (!selectedRepo) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400">
        <RefreshCw className="w-6 h-6 animate-spin text-indigo-400 mb-2" />
        Loading repository details...
      </div>
    );
  }

  const stack = selectedRepo.detected_stack;
  const branches = selectedRepo.branches?.length ? selectedRepo.branches : [selectedRepo.default_branch || 'main', 'main', 'dev'];
  const isIndexingNow = selectedRepo.indexing_status === 'indexing' || isReindexing;

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/repositories')}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReindex}
            disabled={isIndexingNow}
            className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 border border-slate-700 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isIndexingNow ? 'animate-spin' : ''}`} />
            {isIndexingNow ? 'Indexing...' : 'Re-index Chunks'}
          </button>
          <button
            onClick={handleDelete}
            className="px-3 py-1.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-medium flex items-center gap-1.5 border border-rose-500/20"
          >
            <Trash2 className="w-3.5 h-3.5" /> Delete
          </button>
        </div>
      </div>

      {/* Indexing Progress Banner if active */}
      {isIndexingNow && (
        <div className="glass-panel p-4 rounded-xl border border-indigo-500/30 bg-indigo-950/30 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-indigo-300 flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Indexing in progress: <span className="text-white font-mono">{liveIndexStatus?.stage || 'embedding'}</span>
            </span>
            <span className="font-mono text-indigo-400 font-bold">{liveIndexStatus?.progress ?? 15}%</span>
          </div>
          <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
              style={{ width: `${Math.max(10, liveIndexStatus?.progress ?? 15)}%` }}
            />
          </div>
        </div>
      )}

      {/* Main Info Card */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-950/80 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <GitBranch className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white">{selectedRepo.name}</h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-slate-800 text-indigo-300 border border-slate-700">
                  {selectedRepo.provider || 'github'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">{selectedRepo.url}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-[11px] text-slate-400">Indexing Status</p>
              <p className="text-xs font-semibold text-emerald-400 flex items-center gap-1 justify-end mt-0.5">
                {selectedRepo.indexing_status === 'indexed' ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" /> Indexed ({selectedRepo.chunks_count || 0} chunks)
                  </>
                ) : selectedRepo.indexing_status === 'failed' ? (
                  <>
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400" /> Failed
                  </>
                ) : (
                  <>
                    <Clock className="w-3.5 h-3.5 text-amber-400" /> Indexing...
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        {/* AI Stack & Architecture Details */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" /> AI Detected Stack & Toolchain
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Language</p>
              <p className="text-xs font-mono font-semibold text-white mt-1">{stack?.language || selectedRepo.language || 'Detected'}</p>
            </div>
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Framework</p>
              <p className="text-xs font-mono font-semibold text-indigo-300 mt-1">{stack?.framework || 'None / Custom'}</p>
            </div>
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Package Manager</p>
              <p className="text-xs font-mono font-semibold text-slate-300 mt-1">{stack?.package_manager || 'standard'}</p>
            </div>
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Build Tool</p>
              <p className="text-xs font-mono font-semibold text-slate-300 mt-1">{stack?.build_tool || 'default'}</p>
            </div>
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800">
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Test Framework</p>
              <p className="text-xs font-mono font-semibold text-slate-300 mt-1">{stack?.test_framework || 'pytest/jest'}</p>
            </div>
          </div>
        </div>

        {/* Branch Switcher Section */}
        <div className="space-y-3 border-t border-slate-800 pt-6">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-indigo-400" /> Active Branch Manager
          </h3>
          <div className="flex items-center gap-4 bg-slate-900/80 p-4 rounded-xl border border-slate-800">
            <div className="flex-1">
              <p className="text-xs text-slate-300 font-medium">Currently Selected Branch</p>
              <p className="text-xs text-slate-500 mt-0.5">Switching branches will filter AI context retrieval to this branch's code symbols.</p>
            </div>
            <select
              value={targetBranch}
              onChange={(e) => handleBranchSwitch(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-indigo-300 font-mono text-xs px-3 py-2 rounded-xl focus:outline-none focus:border-indigo-500"
            >
              {branches.map((b) => (
                <option key={b} value={b}>
                  {b} {b === (selectedRepo.default_branch || selectedRepo.defaultBranch) ? '(default)' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Edit Metadata */}
        <div className="space-y-3 border-t border-slate-800 pt-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <Edit3 className="w-4 h-4 text-indigo-400" /> Metadata & Description
            </h3>
            <button
              onClick={() => setEditing(!editing)}
              className="text-xs text-indigo-400 hover:underline"
            >
              {editing ? 'Cancel' : 'Edit Metadata'}
            </button>
          </div>

          {editing ? (
            <form onSubmit={handleSave} className="space-y-4 bg-slate-900/80 p-4 rounded-xl border border-slate-800">
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Description</label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>
              <button
                type="submit"
                disabled={isSaving}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5"
              >
                <Check className="w-3.5 h-3.5" /> Save Metadata
              </button>
            </form>
          ) : (
            <p className="text-xs text-slate-300 bg-slate-900/50 p-4 rounded-xl border border-slate-800/60 leading-relaxed">
              {selectedRepo.description || 'No description provided for this repository.'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
