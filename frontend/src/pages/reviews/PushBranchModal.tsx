import React from 'react';
import { X, UploadCloud, Shield, Loader2 } from 'lucide-react';

interface PushBranchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  branchName: string;
  commitSha?: string | null;
}

export const PushBranchModal: React.FC<PushBranchModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
  branchName,
  commitSha,
}) => {
  if (!isOpen) return null;

  const shortSha = commitSha ? commitSha.slice(0, 7) : null;

  return (
    <div
      className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-push-title"
    >
      <div
        className="relative w-full max-w-lg bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-5 space-y-4 animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h3 id="confirm-push-title" className="text-sm font-bold text-slate-100">
                Push AI Fix Branch?
              </h3>
              <p className="text-[11px] text-slate-400">Push to Configured Remote (origin)</p>
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
            Push the dedicated local AI fix branch to your trusted repository remote.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                Branch to Push
              </div>
              <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl font-mono text-blue-300 break-all select-text">
                {branchName}
              </div>
            </div>

            <div className="space-y-1">
              <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                Commit SHA
              </div>
              <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl font-mono text-emerald-300 select-text">
                {shortSha || '—'}
              </div>
            </div>
          </div>

          <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2 text-[11px]">
            <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
              <Shield className="w-3.5 h-3.5 text-blue-400" /> Push Safety Invariants
            </div>
            <ul className="list-disc list-inside space-y-1 text-slate-400">
              <li>
                <strong className="text-slate-300">Exact Ref Push:</strong> Pushes strictly <code className="text-blue-300">{branchName}</code>.
              </li>
              <li>
                <strong className="text-slate-300">Active Branch Preserved:</strong> Your current working branch and HEAD remain untouched.
              </li>
              <li>
                <strong className="text-slate-300">No Force Push:</strong> Non-force push is strictly enforced.
              </li>
              <li>
                <strong className="text-slate-300">No Pull Request:</strong> This action only pushes the branch; no PR is created yet.
              </li>
            </ul>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
          <button
            id="btn-cancel-push"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            id="btn-confirm-push"
            onClick={onConfirm}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white border border-blue-500 shadow-md transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Pushing branch...
              </>
            ) : (
              <>
                <UploadCloud className="w-3.5 h-3.5" />
                Push Branch
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
