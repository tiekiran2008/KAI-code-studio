import React from 'react';
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  Loader2,
  ShieldCheck,
  RefreshCw,
  Clock,
} from 'lucide-react';
import {
  StaticVerificationResult,
  VerificationCheck,
} from '../../api/reviews';

interface StaticVerificationSectionProps {
  result?: StaticVerificationResult | null;
  isApplied: boolean;
  isVerifying: boolean;
  onVerify: () => void;
  verifyError?: string | null;
}

export const StaticVerificationSection: React.FC<StaticVerificationSectionProps> = ({
  result,
  isApplied,
  isVerifying,
  onVerify,
  verifyError,
}) => {
  if (!isApplied) {
    return null;
  }

  const rawStatus = (result?.status || 'not_run').toLowerCase();
  const isPassed = rawStatus === 'passed';
  const isFailed = rawStatus === 'failed';
  const isUnsupported = rawStatus === 'unsupported';
  const isSourceChanged = rawStatus === 'source_changed';
  const isNotRun = rawStatus === 'not_run';

  const formatTimestamp = (ts?: string | null) => {
    if (!ts) return null;
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  };

  const getCheckStatusBadge = (status: VerificationCheck['status']) => {
    const s = (status || '').toLowerCase();
    switch (s) {
      case 'passed':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
            <CheckCircle2 className="w-2.5 h-2.5" /> Passed
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded-full">
            <AlertCircle className="w-2.5 h-2.5" /> Failed
          </span>
        );
      case 'unsupported':
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
            <Info className="w-2.5 h-2.5" /> Unsupported
          </span>
        );
      case 'skipped':
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-400 bg-slate-700/40 border border-slate-700 px-2 py-0.5 rounded-full">
            <Clock className="w-2.5 h-2.5" /> Skipped
          </span>
        );
    }
  };

  return (
    <div className="space-y-3 p-4 rounded-xl border bg-slate-950/60 border-slate-800 transition-all">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div
            className={`p-2 rounded-xl border ${
              isPassed
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : isFailed
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                : isSourceChanged
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : isUnsupported
                ? 'bg-slate-800 border-slate-700 text-slate-400'
                : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold text-slate-200 tracking-wide">
                Tier-1 Static Verification
              </h3>
              {isPassed && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <CheckCircle2 className="w-2.5 h-2.5" /> Static Verification Passed
                </span>
              )}
              {isFailed && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  <AlertCircle className="w-2.5 h-2.5" /> Static Verification Failed
                </span>
              )}
              {isUnsupported && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                  <Info className="w-2.5 h-2.5" /> Verification Unsupported
                </span>
              )}
              {isSourceChanged && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  <AlertTriangle className="w-2.5 h-2.5" /> Source Changed After Apply
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              {isPassed && 'Configured static and syntax checks passed.'}
              {isFailed && 'Static checks identified syntax or structural errors in the applied file.'}
              {isUnsupported && 'Static Verification Not Supported for This Language.'}
              {isSourceChanged &&
                'The current file no longer matches the version that was applied. Static verification was not treated as verification of the original applied fix.'}
              {isNotRun && 'In-memory syntax and merge-conflict verification for applied files.'}
            </p>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-2 shrink-0">
          <button
            id="btn-verify-fix"
            onClick={onVerify}
            disabled={isVerifying}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
              isNotRun
                ? 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500 shadow-sm'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
            } disabled:opacity-50`}
          >
            {isVerifying ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Verifying...
              </>
            ) : (
              <>
                <RefreshCw className="w-3.5 h-3.5" />
                {isNotRun ? 'Verify Fix' : 'Re-run Static Verification'}
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error banner */}
      {verifyError && (
        <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
          <span>{verifyError}</span>
        </div>
      )}

      {/* Metadata Info Bar */}
      {result && !isNotRun && (
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-400 py-1.5 px-2.5 bg-slate-900/60 rounded-lg border border-slate-800/60">
          {result.verified_at && (
            <div>
              <span className="text-slate-500">Last static verification:</span>{' '}
              <span className="text-slate-300 font-mono">
                {formatTimestamp(result.verified_at)}
              </span>
            </div>
          )}
          {result.duration_ms !== null && result.duration_ms !== undefined && (
            <div>
              <span className="text-slate-500">Duration:</span>{' '}
              <span className="text-slate-300 font-mono">{result.duration_ms}ms</span>
            </div>
          )}
          {result.language && (
            <div>
              <span className="text-slate-500">Language:</span>{' '}
              <span className="text-slate-300 font-mono uppercase">{result.language}</span>
            </div>
          )}
          {result.verified_hash && (
            <div className="hidden sm:block">
              <span className="text-slate-500">Hash:</span>{' '}
              <span className="text-slate-400 font-mono text-[10px]">
                {result.verified_hash.slice(0, 10)}...
              </span>
            </div>
          )}
        </div>
      )}

      {/* Structured Checks List */}
      {result && result.checks && result.checks.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 px-1">
            Verification Checks
          </div>
          <div className="divide-y divide-slate-900 border border-slate-800 rounded-lg overflow-hidden bg-slate-900/40">
            {result.checks.map((chk, idx) => (
              <div
                key={`${chk.name}-${idx}`}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 gap-2 text-xs"
              >
                <div className="flex items-start gap-2 min-w-0">
                  <div className="pt-0.5">{getCheckStatusBadge(chk.status)}</div>
                  <div className="min-w-0">
                    <span className="font-mono text-slate-300 font-medium">{chk.name}</span>
                    {chk.message && (
                      <p className="text-[11px] text-slate-400 mt-0.5 break-words">
                        {chk.message}
                      </p>
                    )}
                  </div>
                </div>

                {(chk.line_number !== null && chk.line_number !== undefined) && (
                  <span className="text-[10px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded shrink-0 self-start sm:self-center">
                    Line {chk.line_number}
                    {chk.column !== null && chk.column !== undefined ? `:${chk.column}` : ''}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Structured Errors Panel */}
      {result && result.errors && result.errors.length > 0 && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-rose-300">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" /> Errors
          </div>
          <ul className="space-y-1 text-xs text-rose-200">
            {result.errors.map((err, idx) => (
              <li key={idx} className="font-mono text-[11px] break-words">
                • {err}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Structured Warnings Panel */}
      {result && result.warnings && result.warnings.length > 0 && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Warnings
          </div>
          <ul className="space-y-1 text-xs text-amber-200">
            {result.warnings.map((warn, idx) => (
              <li key={idx} className="text-[11px] break-words">
                • {warn}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Unsupported language advisory notice */}
      {isUnsupported && (
        <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-[11px] text-slate-400 flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
          <span>
            Static syntax verification parser is not available for this language ({result?.language || 'unrecognized'}). This file was not verified.
          </span>
        </div>
      )}
    </div>
  );
};
