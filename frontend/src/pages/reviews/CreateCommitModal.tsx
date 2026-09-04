import React from 'react';
import { X, GitCommit, Shield, Loader2 } from 'lucide-react';

interface CreateCommitModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  filePath: string;
}

export const CreateCommitModal: React.FC<CreateCommitModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
  filePath,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-commit-title"
    >
      <div
        className="relative w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-5 space-y-4 animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <GitCommit className="w-5 h-5" />
            </div>
            <div>
              <h3 id="confirm-commit-title" className="text-sm font-bold text-slate-100">
                Create Local Git Commit?
              </h3>
              <p className="text-[11px] text-slate-400">Dedicated AI Branch Commit</p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
            aria-label="Close confirmation dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-xs text-slate-300">
          <p className="text-slate-300 leading-relaxed">
            Create an isolated local Git commit for this applied and verified fix on a dedicated AI branch.
          </p>

          <div className="space-y-1">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
              Target File to Commit
            </div>
            <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl font-mono text-purple-300 break-all select-text">
              {filePath}
            </div>
          </div>

          <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 text-[11px]">
            <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
              <Shield className="w-3.5 h-3.5 text-purple-400" /> Isolation & Safety Invariants
            </div>
            <ul className="list-disc list-inside space-y-1 text-slate-400">
              <li>
                <strong className="text-slate-300">Dedicated Branch:</strong> Commits to a dedicated AI fix branch (e.g. <code className="text-purple-300">ai-fix/rev-...</code>).
              </li>
              <li>
                <strong className="text-slate-300">Targeted Staging:</strong> Stages strictly this single file using an isolated index.
              </li>
              <li>
                <strong className="text-slate-300">Working Tree Preserved:</strong> Unrelated modified or staged files remain untouched.
              </li>
              <li>
                <strong className="text-slate-300">Active HEAD Unchanged:</strong> Your current branch and active HEAD are not switched.
              </li>
              <li>
                <strong className="text-slate-300">Local Only:</strong> Nothing is pushed to GitHub or remote repositories.
              </li>
            </ul>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
          <button
            id="btn-cancel-commit"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            id="btn-confirm-commit"
            onClick={onConfirm}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white border border-purple-500 shadow-md transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Creating local commit...
              </>
            ) : (
              <>
                <GitCommit className="w-3.5 h-3.5" />
                Create Commit
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
