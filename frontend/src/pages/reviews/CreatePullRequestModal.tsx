import React from 'react';
import { X, GitPullRequest, Shield, Loader2, ArrowRight } from 'lucide-react';

interface CreatePullRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  headBranch: string;
  baseBranch?: string;
  findingIssue?: string;
}

export const CreatePullRequestModal: React.FC<CreatePullRequestModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
  headBranch,
  baseBranch = 'main',
  findingIssue,
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-pr-title"
    >
      <div
        className="relative w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-5 space-y-4 animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
              <GitPullRequest className="w-5 h-5" />
            </div>
            <div>
              <h3 id="confirm-pr-title" className="text-sm font-bold text-slate-100">
                Create GitHub Pull Request?
              </h3>
              <p className="text-[11px] text-slate-400">Open PR from Pushed AI Fix Branch</p>
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
            Open a GitHub Pull Request to propose merging the verified fix into the default repository branch.
          </p>

          {findingIssue && (
            <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl space-y-0.5">
              <div className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Target Issue
              </div>
              <div className="text-slate-200 font-medium truncate">
                {findingIssue}
              </div>
            </div>
          )}

          <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1.5">
            <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
              Branch Mapping
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px] flex-wrap">
              <span className="px-2 py-1 bg-blue-950/60 border border-blue-800/60 rounded-lg text-blue-300 break-all select-text">
                {headBranch}
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
              <span className="px-2 py-1 bg-emerald-950/60 border border-emerald-800/60 rounded-lg text-emerald-300 select-text">
                {baseBranch}
              </span>
            </div>
          </div>

          <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 text-[11px]">
            <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
              <Shield className="w-3.5 h-3.5 text-indigo-400" /> Pull Request Safety Invariants
            </div>
            <ul className="list-disc list-inside space-y-1 text-slate-400">
              <li>
                <strong className="text-slate-300">No Auto-Merge:</strong> The PR will <strong className="text-amber-300">not</strong> be automatically merged or approved.
              </li>
              <li>
                <strong className="text-slate-300">Deterministic Diff:</strong> Proposes only the verified changes committed on <code className="text-blue-300">{headBranch}</code>.
              </li>
              <li>
                <strong className="text-slate-300">Review on GitHub:</strong> You and your team can review CI checks, discuss, and merge directly on GitHub.
              </li>
            </ul>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
          <button
            id="btn-cancel-pr"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            id="btn-confirm-pr"
            onClick={onConfirm}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 shadow-md transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Creating pull request...
              </>
            ) : (
              <>
                <GitPullRequest className="w-3.5 h-3.5" />
                Create Pull Request
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
