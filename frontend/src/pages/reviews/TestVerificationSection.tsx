import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Clock,
  Loader2,
  Play,
  Terminal,
  Cpu,
  Info,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  ServerOff,
} from 'lucide-react';
import { SandboxVerificationResult } from '../../api/reviews';

interface TestVerificationSectionProps {
  result?: SandboxVerificationResult | null;
  isApplied: boolean;
  staticPassed: boolean;
  isRunningTests: boolean;
  onOpenConfirmModal: () => void;
  testError?: string | null;
}

export const TestVerificationSection: React.FC<TestVerificationSectionProps> = ({
  result,
  isApplied,
  staticPassed,
  isRunningTests,
  onOpenConfirmModal,
  testError,
}) => {
  const [showStdout, setShowStdout] = useState(true);
  const [showStderr, setShowStderr] = useState(true);

  if (!isApplied) {
    return null;
  }

  const rawStatus = (result?.status || 'not_run').toLowerCase();
  const isPassed = rawStatus === 'passed';
  const isFailed = rawStatus === 'failed';
  const isTimedOut = rawStatus === 'timed_out';
  const isSandboxUnavailable = rawStatus === 'sandbox_unavailable';
  const isExecutionError = rawStatus === 'execution_error';
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

  const formatDuration = (ms?: number | null) => {
    if (ms === null || ms === undefined) return null;
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
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
                : isTimedOut
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : isSandboxUnavailable || isExecutionError
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                : isSourceChanged
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : isUnsupported
                ? 'bg-slate-800 border-slate-700 text-slate-400'
                : 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
            }`}
          >
            <Terminal className="w-4 h-4" />
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-xs font-bold text-slate-200 tracking-wide">
                Tier-2 Isolated Test Verification
              </h3>

              {isPassed && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <CheckCircle2 className="w-2.5 h-2.5" /> Isolated Tests Passed
                </span>
              )}
              {isFailed && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  <AlertCircle className="w-2.5 h-2.5" /> Isolated Tests Failed
                </span>
              )}
              {isTimedOut && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  <Clock className="w-2.5 h-2.5" /> Test Execution Timed Out
                </span>
              )}
              {isSandboxUnavailable && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-rose-300 border border-rose-500/30">
                  <ServerOff className="w-2.5 h-2.5" /> Sandbox Unavailable
                </span>
              )}
              {isExecutionError && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  <AlertCircle className="w-2.5 h-2.5" /> Sandbox Execution Error
                </span>
              )}
              {isUnsupported && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                  <Info className="w-2.5 h-2.5" /> Isolated Tests Not Supported for This Project
                </span>
              )}
              {isSourceChanged && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  <AlertTriangle className="w-2.5 h-2.5" /> Source Changed Since Apply
                </span>
              )}
            </div>

            <p className="text-[11px] text-slate-400 mt-0.5">
              {isPassed &&
                'Allowed pytest checks completed successfully inside the isolated sandbox.'}
              {isFailed &&
                'Repository pytest checks failed inside the isolated sandbox container.'}
              {isTimedOut &&
                'The sandbox stopped the test execution because the configured execution time limit was exceeded.'}
              {isSandboxUnavailable &&
                'Isolated test execution is currently unavailable.'}
              {isExecutionError &&
                (result?.message || 'An unexpected container sandbox execution error occurred.')}
              {isUnsupported &&
                'Tier-2 container test execution is currently available only for Python projects using pytest.'}
              {isSourceChanged &&
                'Source code was modified after fix application. Re-apply or re-verify to run isolated tests.'}
              {isNotRun &&
                (staticPassed
                  ? 'Run repository pytest suites inside an isolated, network-disabled container.'
                  : 'Tier-1 Static Verification must pass before isolated tests can be executed.')}
            </p>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-2 shrink-0">
          {staticPassed && (
            <button
              id="btn-run-isolated-tests"
              onClick={onOpenConfirmModal}
              disabled={isRunningTests}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                isNotRun
                  ? 'bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-500 shadow-sm'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
              } disabled:opacity-50`}
            >
              {isRunningTests ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Running isolated tests...
                </>
              ) : (
                <>
                  {isNotRun ? (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      Run Isolated Tests
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-3.5 h-3.5" />
                      Re-run Isolated Tests
                    </>
                  )}
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error banner */}
      {testError && (
        <div className="p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
          <span>{testError}</span>
        </div>
      )}

      {/* Resource Limit Hit Notice */}
      {result?.resource_limit_hit && (
        <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-300 flex items-start gap-2">
          <Cpu className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <span>
            Container reached memory (512MB) or PID limits during execution and was terminated.
          </span>
        </div>
      )}

      {/* Metadata & Test Counts Bar */}
      {result && !isNotRun && (
        <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-400 py-1.5 px-2.5 bg-slate-900/60 rounded-lg border border-slate-800/60">
          {result.tests_total !== null && result.tests_total !== undefined && (
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-300">
                Tests: {result.tests_total} Total
              </span>
              {result.tests_passed !== null && result.tests_passed !== undefined && (
                <span className="text-emerald-400 font-semibold">
                  • {result.tests_passed} Passed
                </span>
              )}
              {result.tests_failed !== null && result.tests_failed !== undefined && (
                <span className="text-rose-400 font-semibold">
                  • {result.tests_failed} Failed
                </span>
              )}
              {result.tests_skipped !== null && result.tests_skipped !== undefined && result.tests_skipped > 0 && (
                <span className="text-slate-400">
                  • {result.tests_skipped} Skipped
                </span>
              )}
            </div>
          )}

          {result.duration_ms !== null && result.duration_ms !== undefined && (
            <div>
              <span className="text-slate-500">Duration:</span>{' '}
              <span className="text-slate-300 font-mono">
                {formatDuration(result.duration_ms)}
              </span>
            </div>
          )}

          {result.exit_code !== null && result.exit_code !== undefined && (
            <div>
              <span className="text-slate-500">Exit Code:</span>{' '}
              <span className="text-slate-300 font-mono">{result.exit_code}</span>
            </div>
          )}

          {result.verified_at && (
            <div>
              <span className="text-slate-500">Verified:</span>{' '}
              <span className="text-slate-300 font-mono">
                {formatTimestamp(result.verified_at)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Stdout Output Panel */}
      {result?.stdout_summary && (
        <div className="space-y-1 rounded-lg border border-slate-800 overflow-hidden bg-slate-950">
          <button
            onClick={() => setShowStdout(!showStdout)}
            className="w-full flex items-center justify-between p-2 text-xs font-semibold text-slate-300 bg-slate-900/60 hover:bg-slate-900 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              {showStdout ? (
                <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
              )}
              <span>Standard Output (stdout)</span>
            </div>
            {result.stdout_summary.length >= 65536 && (
              <span className="text-[10px] text-amber-400 font-mono">Output truncated</span>
            )}
          </button>

          {showStdout && (
            <pre className="p-3 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-56 overflow-y-auto whitespace-pre-wrap select-text">
              {result.stdout_summary}
            </pre>
          )}
        </div>
      )}

      {/* Stderr Output Panel */}
      {result?.stderr_summary && (
        <div className="space-y-1 rounded-lg border border-slate-800 overflow-hidden bg-slate-950">
          <button
            onClick={() => setShowStderr(!showStderr)}
            className="w-full flex items-center justify-between p-2 text-xs font-semibold text-rose-300 bg-slate-900/60 hover:bg-slate-900 transition-colors"
          >
            <div className="flex items-center gap-1.5">
              {showStderr ? (
                <ChevronDown className="w-3.5 h-3.5 text-rose-400" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5 text-rose-400" />
              )}
              <span>Standard Error (stderr)</span>
            </div>
            {result.stderr_summary.length >= 65536 && (
              <span className="text-[10px] text-amber-400 font-mono">Output truncated</span>
            )}
          </button>

          {showStderr && (
            <pre className="p-3 text-[11px] font-mono text-rose-300 overflow-x-auto max-h-56 overflow-y-auto whitespace-pre-wrap select-text">
              {result.stderr_summary}
            </pre>
          )}
        </div>
      )}

      {/* Unsupported advisory notice */}
      {isUnsupported && (
        <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-[11px] text-slate-400 flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
          <span>
            Tier-2 isolated container testing is not configured for this framework/language. No tests were executed.
          </span>
        </div>
      )}
    </div>
  );
};
