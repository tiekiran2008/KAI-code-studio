import React from 'react';
import {
  ShieldAlert,
  Play,
  X,
  Lock,
  Cpu,
  WifiOff,
  PackageX,
  FileCheck,
  Loader2,
} from 'lucide-react';

interface RunIsolatedTestsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
}

export const RunIsolatedTestsModal: React.FC<RunIsolatedTestsModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
}) => {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-run-tests-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden animate-scale-up">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-950/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-xl">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 id="modal-run-tests-title" className="text-sm font-bold text-slate-100">
                Run Isolated Tests Confirmation
              </h3>
              <p className="text-xs text-slate-400">
                Execute pytest checks inside a sandboxed container
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Content */}
        <div className="p-5 space-y-4">
          <p className="text-xs text-slate-300 leading-relaxed">
            You are about to run tests for this applied fix inside an ephemeral sandbox container.
            Please review the security and execution parameters:
          </p>

          <div className="space-y-2 text-xs">
            <div className="flex items-start gap-2.5 p-2.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <WifiOff className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Network Disabled</span>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Containers execute with zero outbound or inbound network access.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-2.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <PackageX className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">No Auto-Dependency Install</span>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Package installation (pip) is disabled. Tests run using pre-bundled standard test harnesses.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-2.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <FileCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Ephemeral Copy Protected</span>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Tests run on a temporary copy. Your local repository files are never modified by test execution.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-2.5 p-2.5 bg-slate-950/60 border border-slate-800 rounded-xl">
              <Cpu className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-slate-200">Resource & Time Limits</span>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Enforced hard timeout of 30 seconds, 512MB RAM, and non-root execution.
                </p>
              </div>
            </div>
          </div>

          <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-[11px] text-indigo-300 flex items-start gap-2">
            <Lock className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <span>
              <strong>Supported Stacks:</strong> Tier-2 isolated container testing currently supports Python + pytest projects only.
            </span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-2.5 p-4 border-t border-slate-800 bg-slate-950/50">
          <button
            id="btn-cancel-run-tests"
            onClick={onClose}
            disabled={isLoading}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:bg-slate-800 border border-slate-700 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            id="btn-confirm-run-tests"
            onClick={onConfirm}
            disabled={isLoading}
            aria-label="Run Tests"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 shadow-md transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Running isolated tests...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                Run Tests
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
