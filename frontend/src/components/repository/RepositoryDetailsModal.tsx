import React from 'react';
import { GitBranch, X, Database, Code, CheckCircle2, Clock } from 'lucide-react';
import { Repository } from '../../types';

interface RepositoryDetailsModalProps {
  repository: Repository | null;
  onClose: () => void;
}

export const RepositoryDetailsModal: React.FC<RepositoryDetailsModalProps> = ({ repository, onClose }) => {
  if (!repository) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#0f172a] border border-indigo-500/30 rounded-2xl max-w-lg w-full p-6 space-y-6 shadow-2xl animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-indigo-400" />
            <h3 className="text-lg font-bold text-white">{repository.name}</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-3 rounded-xl space-y-1">
              <div className="text-slate-400 flex items-center gap-1">
                <Code className="w-3.5 h-3.5 text-indigo-400" /> Total Chunks
              </div>
              <div className="text-base font-bold text-white">{repository.chunksCount}</div>
            </div>
            <div className="glass-card p-3 rounded-xl space-y-1">
              <div className="text-slate-400 flex items-center gap-1">
                <Database className="w-3.5 h-3.5 text-indigo-400" /> Vector Collection
              </div>
              <div className="text-sm font-bold text-indigo-300 font-mono">qdrant_repo_index</div>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="text-slate-400 font-medium">Repository URL / Location</div>
            <div className="p-2.5 rounded-xl bg-slate-900 font-mono text-slate-200 border border-slate-800 break-all">
              {repository.url}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <div className="text-slate-400 font-medium">Language Stack</div>
              <div className="p-2 rounded-xl bg-slate-900 text-slate-200 font-mono border border-slate-800">
                {repository.language}
              </div>
            </div>
            <div className="space-y-1.5">
              <div className="text-slate-400 font-medium">Indexing Status</div>
              <div className="p-2 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-2">
                {repository.indexingStatus === 'indexed' ? (
                  <span className="text-emerald-400 font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Indexed
                  </span>
                ) : (
                  <span className="text-amber-400 font-medium flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" /> Processing...
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="text-slate-400 font-medium">Available Branches ({repository.branches.length})</div>
            <div className="flex flex-wrap gap-1.5">
              {repository.branches.map((b) => (
                <span
                  key={b}
                  className={`px-2 py-1 rounded text-[11px] font-mono border ${
                    b === repository.currentBranch
                      ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/40'
                      : 'bg-slate-900 text-slate-400 border-slate-800'
                  }`}
                >
                  {b} {b === repository.currentBranch && '(active)'}
                </span>
              ))}
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="text-slate-400 font-medium">Last Indexed Timestamp</div>
            <div className="text-slate-300 font-mono">
              {new Date(repository.lastIndexedAt).toLocaleString()}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 text-xs font-medium text-slate-300 hover:text-white"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
