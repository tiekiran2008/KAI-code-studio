import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Check,
  Ban,
  FileCode,
  GitCompare,
  Code2,
  Columns,
  Loader2,
  Info,
  AlertTriangle,
  ShieldCheck,
  RotateCcw,
  Undo2,
} from 'lucide-react';
import {
  reviewsApi,
  ReviewFinding,
  FixSuggestion,
} from '../../api/reviews';
import { StaticVerificationSection } from './StaticVerificationSection';
import { TestVerificationSection } from './TestVerificationSection';
import { RunIsolatedTestsModal } from './RunIsolatedTestsModal';
import { CommitSection } from './CommitSection';
import { CreateCommitModal } from './CreateCommitModal';
import { PushBranchModal } from './PushBranchModal';
import { CreatePullRequestModal } from './CreatePullRequestModal';
import { FixWorkflowStepper } from './FixWorkflowStepper';

interface FixSuggestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  reviewId: string;
  findingIndex: number;
  finding: ReviewFinding;
  fixSuggestion: FixSuggestion;
  onDecisionChange: (updatedFix: FixSuggestion) => void;
}

type CodeViewMode = 'diff' | 'side-by-side' | 'proposed' | 'original';

export const FixSuggestionModal: React.FC<FixSuggestionModalProps> = ({
  isOpen,
  onClose,
  reviewId,
  findingIndex,
  finding,
  fixSuggestion,
  onDecisionChange,
}) => {
  const [viewMode, setViewMode] = useState<CodeViewMode>('diff');
  const [actionLoading, setActionLoading] = useState<'accept' | 'reject' | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [isApplying, setIsApplying] = useState<boolean>(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [staleError, setStaleError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [isRunningTests, setIsRunningTests] = useState<boolean>(false);
  const [testVerifyError, setTestVerifyError] = useState<string | null>(null);
  const [showRunTestsModal, setShowRunTestsModal] = useState<boolean>(false);
  const [isCommitting, setIsCommitting] = useState<boolean>(false);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [showCreateCommitModal, setShowCreateCommitModal] = useState<boolean>(false);
  const [isPushing, setIsPushing] = useState<boolean>(false);
  const [pushError, setPushError] = useState<string | null>(null);
  const [showPushBranchModal, setShowPushBranchModal] = useState<boolean>(false);
  const [isCreatingPR, setIsCreatingPR] = useState<boolean>(false);
  const [prError, setPrError] = useState<string | null>(null);
  const [showCreatePRModal, setShowCreatePRModal] = useState<boolean>(false);
  const [isRegenerating, setIsRegenerating] = useState<boolean>(false);
  const [isRollingBack, setIsRollingBack] = useState<boolean>(false);
  const [rollbackError, setRollbackError] = useState<string | null>(null);
  const [showRollbackConfirmModal, setShowRollbackConfirmModal] = useState<boolean>(false);

  // Close on Escape key (unless confirmation dialog is open)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (showConfirmModal) {
          setShowConfirmModal(false);
        } else if (showRollbackConfirmModal) {
          setShowRollbackConfirmModal(false);
        } else if (showRunTestsModal) {
          setShowRunTestsModal(false);
        } else if (showCreateCommitModal) {
          setShowCreateCommitModal(false);
        } else if (showPushBranchModal) {
          setShowPushBranchModal(false);
        } else if (showCreatePRModal) {
          setShowCreatePRModal(false);
        } else if (isOpen) {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, showConfirmModal, showRollbackConfirmModal, showRunTestsModal, showCreateCommitModal, showPushBranchModal, showCreatePRModal, onClose]);

  if (!isOpen) return null;

  const handleDecision = async (decision: 'accept' | 'reject') => {
    setActionLoading(decision);
    setActionError(null);
    try {
      if (decision === 'accept') {
        const res = await reviewsApi.acceptFix(reviewId, findingIndex);
        onDecisionChange(res.fix_suggestion);
      } else {
        const res = await reviewsApi.rejectFix(reviewId, findingIndex);
        onDecisionChange(res.fix_suggestion);
      }
    } catch (err: any) {
      setActionError(err?.message || `Failed to ${decision} suggestion`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenerate = async () => {
    if (isRegenerating) return;
    setIsRegenerating(true);
    setActionError(null);
    try {
      const res = await reviewsApi.regenerateFix(reviewId, findingIndex);
      onDecisionChange(res.fix_suggestion);
    } catch (err: any) {
      setActionError(err?.message || 'Failed to regenerate fix suggestion');
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleOpenConfirmRollback = () => {
    setRollbackError(null);
    setShowRollbackConfirmModal(true);
  };

  const handleCancelConfirmRollback = () => {
    setShowRollbackConfirmModal(false);
  };

  const handleConfirmRollback = async () => {
    if (isRollingBack) return;
    setIsRollingBack(true);
    setRollbackError(null);
    try {
      const res = await reviewsApi.rollbackFix(reviewId, findingIndex);
      setShowRollbackConfirmModal(false);
      onDecisionChange(res.fix_suggestion);
    } catch (err: any) {
      setRollbackError(err?.message || 'Failed to rollback fix');
    } finally {
      setIsRollingBack(false);
    }
  };

  const handleOpenConfirmApply = () => {
    setApplyError(null);
    setStaleError(null);
    setShowConfirmModal(true);
  };

  const handleCancelConfirmApply = () => {
    setShowConfirmModal(false);
  };

  const handleConfirmApply = async () => {
    if (isApplying) return; // Prevent duplicate concurrent submission
    setIsApplying(true);
    setApplyError(null);
    setStaleError(null);

    try {
      const res = await reviewsApi.applyFix(reviewId, findingIndex);
      onDecisionChange(res.fix_suggestion);
      setShowConfirmModal(false);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to apply fix to file.';
      const isStale =
        err?.status === 409 ||
        errorMsg.toLowerCase().includes('stale source') ||
        errorMsg.toLowerCase().includes('stale');

      if (isStale) {
        const staleMsg = 'Source changed after this suggestion was generated. This fix was not applied.';
        setStaleError(staleMsg);
        onDecisionChange({
          ...fixSuggestion,
          application_status: 'stale',
          application_error: staleMsg,
        });
      } else {
        setApplyError(errorMsg);
        onDecisionChange({
          ...fixSuggestion,
          application_status: 'apply_failed',
          application_error: errorMsg,
        });
      }
      setShowConfirmModal(false);
    } finally {
      setIsApplying(false);
    }
  };

  const handleVerifyFix = async () => {
    if (isVerifying) return; // Prevent duplicate requests
    setIsVerifying(true);
    setVerifyError(null);

    try {
      const res = await reviewsApi.verifyFix(reviewId, findingIndex);
      onDecisionChange(res.fix_suggestion);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to perform static verification.';
      const isSourceChanged =
        err?.status === 409 ||
        errorMsg.toLowerCase().includes('source changed') ||
        errorMsg.toLowerCase().includes('hash mismatch') ||
        errorMsg.toLowerCase().includes('stale');

      if (isSourceChanged) {
        const changedMsg =
          'The current file no longer matches the version that was applied. Static verification was not treated as verification of the original applied fix.';
        setVerifyError(changedMsg);
        onDecisionChange({
          ...fixSuggestion,
          static_verification: {
            status: 'source_changed',
            checks: [],
            errors: [changedMsg],
            warnings: [],
            message: changedMsg,
          },
        });
      } else {
        setVerifyError(errorMsg);
      }
    } finally {
      setIsVerifying(false);
    }
  };

  const handleOpenRunTestsModal = () => {
    setTestVerifyError(null);
    setShowRunTestsModal(true);
  };

  const handleConfirmRunTests = async () => {
    if (isRunningTests) return; // Prevent duplicate requests
    setIsRunningTests(true);
    setTestVerifyError(null);

    try {
      const res = await reviewsApi.verifyFixTests(reviewId, findingIndex);
      onDecisionChange(res.fix_suggestion);
      setShowRunTestsModal(false);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to execute isolated tests.';
      const isSourceChanged =
        err?.status === 409 &&
        (errorMsg.toLowerCase().includes('source') ||
          errorMsg.toLowerCase().includes('modified') ||
          errorMsg.toLowerCase().includes('hash'));

      if (isSourceChanged) {
        const changedMsg =
          'Source file was modified after fix was applied. Cannot run isolated tests on stale source.';
        setTestVerifyError(changedMsg);
        onDecisionChange({
          ...fixSuggestion,
          test_verification: {
            status: 'source_changed',
            verification_type: 'isolated_tests',
            test_framework: 'pytest',
            command_label: 'pytest',
            exit_code: null,
            duration_ms: 0,
            stdout_summary: '',
            stderr_summary: '',
            timed_out: false,
            resource_limit_hit: false,
            message: changedMsg,
          },
        });
      } else {
        setTestVerifyError(errorMsg);
      }
      setShowRunTestsModal(false);
    } finally {
      setIsRunningTests(false);
    }
  };

  const handleOpenCreateCommitModal = () => {
    setCommitError(null);
    setShowCreateCommitModal(true);
  };

  const handleConfirmCreateCommit = async () => {
    if (isCommitting) return; // Prevent duplicate requests
    setIsCommitting(true);
    setCommitError(null);

    try {
      const res = await reviewsApi.createFixCommit(reviewId, findingIndex);
      onDecisionChange(res.fix_suggestion);
      setShowCreateCommitModal(false);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to create local Git commit.';
      const isSourceChanged =
        err?.status === 409 &&
        (errorMsg.toLowerCase().includes('source') ||
          errorMsg.toLowerCase().includes('modified') ||
          errorMsg.toLowerCase().includes('stale'));

      if (isSourceChanged) {
        const changedMsg =
          'Source file was modified after fix was applied. Cannot commit stale source.';
        setCommitError(changedMsg);
      } else {
        setCommitError(errorMsg);
      }
      setShowCreateCommitModal(false);
    } finally {
      setIsCommitting(false);
    }
  };

  const handleOpenPushBranchModal = () => {
    setPushError(null);
    setShowPushBranchModal(true);
  };

  const handleConfirmPushBranch = async () => {
    if (isPushing) return; // Prevent duplicate requests
    setIsPushing(true);
    setPushError(null);

    try {
      const res = await reviewsApi.pushFixBranch(reviewId, findingIndex);
      onDecisionChange(res.fix_suggestion);
      setShowPushBranchModal(false);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to push AI fix branch.';
      setPushError(errorMsg);
      setShowPushBranchModal(false);
    } finally {
      setIsPushing(false);
    }
  };

  const handleOpenCreatePRModal = () => {
    setPrError(null);
    setShowCreatePRModal(true);
  };

  const handleConfirmCreatePR = async () => {
    if (isCreatingPR) return; // Prevent duplicate requests
    setIsCreatingPR(true);
    setPrError(null);

    try {
      const res = await reviewsApi.createFixPullRequest(reviewId, findingIndex);
      onDecisionChange(res.fix_suggestion);
      setShowCreatePRModal(false);
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to create GitHub Pull Request.';
      setPrError(errorMsg);
      setShowCreatePRModal(false);
    } finally {
      setIsCreatingPR(false);
    }
  };

  const confidencePercent = Math.min(
    100,
    Math.max(0, Math.round((fixSuggestion.confidence_score ?? 1.0) * 100))
  );

  // Render unified diff safely line-by-line as pure text
  const renderUnifiedDiff = () => {
    const lines = (fixSuggestion.diff || '').split('\n');
    if (!lines.length || !fixSuggestion.diff) {
      return (
        <div className="p-4 text-xs text-slate-500 font-mono italic">
          No diff representation available.
        </div>
      );
    }

    return (
      <div className="font-mono text-xs overflow-x-auto max-h-[420px] overflow-y-auto bg-slate-950 border border-slate-800 rounded-xl divide-y divide-slate-900/60 select-text">
        {lines.map((line, idx) => {
          let lineStyle = 'bg-slate-950 text-slate-300 px-4 py-1';

          if (line.startsWith('---') || line.startsWith('+++')) {
            lineStyle =
              'bg-slate-900/90 text-slate-400 font-bold px-4 py-1.5 border-b border-slate-800';
          } else if (line.startsWith('@@')) {
            lineStyle =
              'bg-cyan-950/40 text-cyan-300 font-semibold px-4 py-1.5 border-y border-cyan-900/40';
          } else if (line.startsWith('+')) {
            lineStyle =
              'bg-emerald-950/40 text-emerald-300 px-4 py-1 border-l-2 border-emerald-500';
          } else if (line.startsWith('-')) {
            lineStyle =
              'bg-rose-950/40 text-rose-300 px-4 py-1 border-l-2 border-rose-500';
          }

          return (
            <div key={idx} className={`flex items-start whitespace-pre ${lineStyle}`}>
              <span className="w-8 text-[10px] text-slate-600 select-none shrink-0 text-right pr-3 pt-0.5">
                {idx + 1}
              </span>
              <span className="flex-1 overflow-x-auto">{line}</span>
            </div>
          );
        })}
      </div>
    );
  };

  const renderSingleCodeBlock = (
    code: string,
    label: string,
    variant: 'original' | 'proposed'
  ) => {
    const isProposed = variant === 'proposed';
    return (
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs text-slate-400 px-1 font-medium">
          <span>{label}</span>
          <span className="text-[10px] font-mono text-slate-500">
            {code.split('\n').length} lines
          </span>
        </div>
        <pre
          className={`font-mono text-xs p-4 overflow-x-auto max-h-[420px] overflow-y-auto rounded-xl border whitespace-pre select-text ${
            isProposed
              ? 'bg-slate-950 border-emerald-500/30 text-emerald-200'
              : 'bg-slate-950 border-slate-800 text-slate-300'
          }`}
        >
          <code>{code}</code>
        </pre>
      </div>
    );
  };

  const isApplied = fixSuggestion.application_status === 'applied';
  const isStale = fixSuggestion.application_status === 'stale' || Boolean(staleError);
  const isApplyFailed =
    fixSuggestion.application_status === 'apply_failed' || Boolean(applyError);
  const isAccepted = fixSuggestion.user_decision === 'accepted';
  const isRejected = fixSuggestion.user_decision === 'rejected';
  const isValidationInvalid = fixSuggestion.validation_status === 'invalid';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="fix-suggestion-title"
    >
      <div
        className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-slate-800 bg-slate-900/90">
          <div className="space-y-1.5 pr-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                <Sparkles className="w-3.5 h-3.5" /> Automated Fix Suggestion
              </span>

              {/* Validation status badge */}
              {fixSuggestion.validation_status === 'valid' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  <CheckCircle2 className="w-3 h-3" /> Valid Syntax
                </span>
              )}
              {fixSuggestion.validation_status === 'invalid' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  <AlertCircle className="w-3 h-3" /> Syntax Warning
                </span>
              )}
              {fixSuggestion.validation_status === 'pending' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                  <Clock className="w-3 h-3" /> Validation Pending
                </span>
              )}

              {/* Confidence score badge */}
              <span className="text-[11px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded-md border border-slate-700">
                {confidencePercent}% Confidence
              </span>

              {/* Current user decision badge */}
              {isAccepted && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  <Check className="w-3 h-3" /> Accepted Suggestion
                </span>
              )}
              {isRejected && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                  <Ban className="w-3 h-3" /> Rejected Suggestion
                </span>
              )}

              {/* Application status badge */}
              {isApplied && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  <CheckCircle2 className="w-3 h-3" /> Applied to File
                </span>
              )}
              {/* Static verification status badge */}
              {isApplied && fixSuggestion.static_verification && (
                <>
                  {fixSuggestion.static_verification.status === 'passed' && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      <CheckCircle2 className="w-3 h-3" /> Static Verification Passed
                    </span>
                  )}
                  {fixSuggestion.static_verification.status === 'failed' && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                      <AlertCircle className="w-3 h-3" /> Static Verification Failed
                    </span>
                  )}
                  {fixSuggestion.static_verification.status === 'unsupported' && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                      <Info className="w-3 h-3" /> Verification Unsupported
                    </span>
                  )}
                  {fixSuggestion.static_verification.status === 'source_changed' && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                      <AlertTriangle className="w-3 h-3" /> Source Changed After Apply
                    </span>
                  )}
                </>
              )}
              {isStale && !isApplied && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  <AlertCircle className="w-3 h-3" /> Stale Source
                </span>
              )}
              {isApplyFailed && !isApplied && !isStale && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                  <AlertCircle className="w-3 h-3" /> Apply Failed
                </span>
              )}
              {fixSuggestion.application_status === 'applying' && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                  <Loader2 className="w-3 h-3 animate-spin" /> Applying...
                </span>
              )}
            </div>

            <h2 id="fix-suggestion-title" className="text-base font-bold text-slate-100">
              {finding.issue}
            </h2>

            {fixSuggestion.file_path && (
              <div className="text-xs text-indigo-300 font-mono flex items-center gap-1.5">
                <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                <span>
                  {fixSuggestion.file_path}
                  {finding.line_number ? `:${finding.line_number}` : ''}
                </span>
              </div>
            )}
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Linear AI Fix & PR Lifecycle Stepper */}
          <FixWorkflowStepper
            finding={finding}
            fixSuggestion={fixSuggestion}
            variant="full"
          />

          {/* Action error banner */}
          {actionError && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{actionError}</span>
            </div>
          )}

          {/* Stale Source Notice */}
          {isStale && !isApplied && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-300 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <strong>Stale Source Detected:</strong>{' '}
                {staleError ||
                  fixSuggestion.application_error ||
                  'Source changed after this suggestion was generated. This fix was not applied.'}
              </div>
            </div>
          )}

          {/* Apply Failed Notice */}
          {isApplyFailed && !isApplied && !isStale && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <strong>Apply Failed:</strong>{' '}
                {applyError ||
                  fixSuggestion.application_error ||
                  'Failed to apply fix to file. Please check repository state.'}
              </div>
            </div>
          )}

          {/* Applied Success Notice */}
          {isApplied && (
            <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-xl text-xs text-cyan-300 flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <strong>Fix Applied:</strong> This fix has been written to the local repository file.
                {fixSuggestion.applied_at && (
                  <span className="block text-[11px] text-cyan-400/80 font-mono mt-0.5">
                    Applied at: {fixSuggestion.applied_at}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Tier-1 Static Verification Section */}
          {isApplied && (
            <StaticVerificationSection
              result={fixSuggestion.static_verification}
              isApplied={isApplied}
              isVerifying={isVerifying}
              onVerify={handleVerifyFix}
              verifyError={verifyError}
            />
          )}

          {/* Tier-2 Isolated Container Test Verification Section */}
          {isApplied && (
            <TestVerificationSection
              result={fixSuggestion.test_verification}
              isApplied={isApplied}
              staticPassed={fixSuggestion.static_verification?.status === 'passed'}
              isRunningTests={isRunningTests}
              onOpenConfirmModal={handleOpenRunTestsModal}
              testError={testVerifyError}
            />
          )}

          {/* Phase 11.5B-3/B-4/B-5 Local Git Commit, Push & PR Section */}
          <CommitSection
            gitCommit={fixSuggestion.git_commit}
            gitPush={fixSuggestion.git_push}
            gitPullRequest={fixSuggestion.git_pull_request}
            isApplied={isApplied}
            staticPassed={fixSuggestion.static_verification?.status === 'passed'}
            isCommitting={isCommitting}
            isPushing={isPushing}
            isCreatingPR={isCreatingPR}
            onOpenConfirmModal={handleOpenCreateCommitModal}
            onOpenPushModal={handleOpenPushBranchModal}
            onOpenPRModal={handleOpenCreatePRModal}
            commitError={commitError}
            pushError={pushError}
            prError={prError}
          />

          {/* Explanation Box */}
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 space-y-1.5">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-indigo-400" /> Explanation
            </div>
            <p className="text-xs text-slate-200 leading-relaxed">
              {fixSuggestion.explanation}
            </p>
            {fixSuggestion.validation_message && (
              <div className="pt-1.5 border-t border-slate-800/60 text-[11px] text-slate-400 italic">
                Note: {fixSuggestion.validation_message}
              </div>
            )}
          </div>

          {/* View Mode Switcher */}
          <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div className="flex gap-1 p-0.5 bg-slate-950 rounded-lg border border-slate-800">
              <button
                id="tab-diff"
                onClick={() => setViewMode('diff')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  viewMode === 'diff'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <GitCompare className="w-3.5 h-3.5" /> Unified Diff
              </button>
              <button
                id="tab-side-by-side"
                onClick={() => setViewMode('side-by-side')}
                className={`hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  viewMode === 'side-by-side'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Columns className="w-3.5 h-3.5" /> Side-by-Side
              </button>
              <button
                id="tab-proposed"
                onClick={() => setViewMode('proposed')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  viewMode === 'proposed'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" /> Proposed Code
              </button>
              <button
                id="tab-original"
                onClick={() => setViewMode('original')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  viewMode === 'original'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <FileCode className="w-3.5 h-3.5" /> Original Code
              </button>
            </div>

            <span className="text-[11px] text-slate-500 font-mono hidden sm:inline">
              Language: {fixSuggestion.language || 'generic'}
            </span>
          </div>

          {/* Code display based on viewMode */}
          <div className="space-y-2">
            {viewMode === 'diff' && renderUnifiedDiff()}

            {viewMode === 'side-by-side' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {renderSingleCodeBlock(
                  fixSuggestion.original_code,
                  'Original Code',
                  'original'
                )}
                {renderSingleCodeBlock(
                  fixSuggestion.proposed_code,
                  'Proposed Fix',
                  'proposed'
                )}
              </div>
            )}

            {viewMode === 'proposed' &&
              renderSingleCodeBlock(
                fixSuggestion.proposed_code,
                'Proposed Fixed Snippet',
                'proposed'
              )}

            {viewMode === 'original' &&
              renderSingleCodeBlock(
                fixSuggestion.original_code,
                'Original Source Snippet',
                'original'
              )}
          </div>

          {/* Advisory Notice */}
          <div className="p-3 bg-slate-950/40 border border-slate-800 rounded-xl text-[11px] text-slate-400 flex items-center gap-2">
            <Info className="w-4 h-4 text-slate-500 shrink-0" />
            <span>
              <strong>Accept vs Apply:</strong> Accepting approves the recommendation for tracking. Applying will directly modify your local workspace file after explicit confirmation.
            </span>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 border-t border-slate-800 bg-slate-900/90">
          <div className="text-xs text-slate-400 font-medium">
            Current Decision:{' '}
            <strong className="capitalize text-slate-200">
              {fixSuggestion.user_decision || 'Pending'}
            </strong>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto justify-end">
            <button
              onClick={onClose}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-colors"
            >
              Close
            </button>

            {/* Regenerate Button (when not applied) */}
            {!isApplied && (
              <button
                id="btn-regenerate-fix"
                onClick={handleRegenerate}
                disabled={isRegenerating || actionLoading !== null || isApplying}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/30 transition-colors disabled:opacity-50"
                title="Regenerate patch suggestion with AI"
              >
                {isRegenerating ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                ) : (
                  <RotateCcw className="w-3.5 h-3.5 text-indigo-400" />
                )}
                {isRegenerating ? 'Regenerating...' : 'Regenerate'}
              </button>
            )}

            {/* Reject Button */}
            <button
              id="btn-reject-suggestion"
              onClick={() => handleDecision('reject')}
              disabled={actionLoading !== null || isApplying}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
                isRejected
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 opacity-70'
                  : 'bg-rose-600/10 text-rose-400 border-rose-500/30 hover:bg-rose-600/20 hover:border-rose-500/50'
              } disabled:opacity-50`}
            >
              {actionLoading === 'reject' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Ban className="w-3.5 h-3.5" />
              )}
              {isRejected ? 'Rejected Suggestion' : 'Reject Suggestion'}
            </button>

            {/* Accept Button */}
            <button
              id="btn-accept-suggestion"
              onClick={() => handleDecision('accept')}
              disabled={actionLoading !== null || isApplying}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold border transition-all ${
                isAccepted
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 opacity-70'
                  : 'bg-emerald-600 text-white border-emerald-500 hover:bg-emerald-500 shadow-md'
              } disabled:opacity-50`}
            >
              {actionLoading === 'accept' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Check className="w-3.5 h-3.5" />
              )}
              {isAccepted ? 'Accepted Suggestion' : 'Accept Suggestion'}
            </button>

            {/* Apply & Rollback Buttons */}
            {isAccepted && (
              <>
                {isApplied ? (
                  <>
                    <button
                      id="btn-rollback-fix"
                      onClick={handleOpenConfirmRollback}
                      disabled={isRollingBack || isVerifying}
                      className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-all disabled:opacity-50"
                    >
                      {isRollingBack ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Undo2 className="w-3.5 h-3.5" />
                      )}
                      Rollback Fix
                    </button>
                    <button
                      id="btn-applied-status"
                      disabled
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 cursor-default opacity-90"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Applied
                    </button>
                    <button
                      id="btn-verify-fix-modal"
                      onClick={handleVerifyFix}
                      disabled={isVerifying || actionLoading !== null || isApplying}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 shadow-md transition-all disabled:opacity-50"
                    >
                      {isVerifying ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          Verifying...
                        </>
                      ) : (
                        <>
                          <ShieldCheck className="w-3.5 h-3.5" />
                          {fixSuggestion.static_verification &&
                          fixSuggestion.static_verification.status !== 'not_run'
                            ? 'Re-run Static Verification'
                            : 'Verify Fix'}
                        </>
                      )}
                    </button>
                  </>
                ) : (
                  !isValidationInvalid && (
                    <button
                      id="btn-apply-suggestion"
                      onClick={handleOpenConfirmApply}
                      disabled={actionLoading !== null || isApplying}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white border border-cyan-500 shadow-md transition-all disabled:opacity-50"
                    >
                      <FileCode className="w-3.5 h-3.5" /> Apply Suggestion
                    </button>
                  )
                )}
              </>
            )}
          </div>
        </div>

        {/* Phase 11.3B-4 Explicit Confirmation Modal */}
        {showConfirmModal && (
          <div
            className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-150"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-apply-title"
          >
            <div
              className="relative w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-5 space-y-4 animate-in zoom-in-95 duration-150"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                    <FileCode className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 id="confirm-apply-title" className="text-sm font-bold text-slate-100">
                      Apply Fix to Local File
                    </h3>
                    <p className="text-[11px] text-slate-400">Explicit Confirmation Required</p>
                  </div>
                </div>
                <button
                  onClick={handleCancelConfirmApply}
                  disabled={isApplying}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
                  aria-label="Close confirmation dialog"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="space-y-2.5 text-xs text-slate-300">
                <p>
                  This action will directly modify your local repository workspace file using the accepted fix patch.
                </p>

                <div className="space-y-1">
                  <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                    Target File
                  </div>
                  <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl font-mono text-indigo-300 break-all select-text">
                    {fixSuggestion.file_path}
                  </div>
                </div>

                <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl text-[11px] text-slate-400 space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
                    <Info className="w-3.5 h-3.5 text-cyan-400" /> Operational Notice
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                    <li>Tests are not automatically executed.</li>
                    <li>No Git commit or push is performed.</li>
                  </ul>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  id="btn-cancel-apply"
                  onClick={handleCancelConfirmApply}
                  disabled={isApplying}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  id="btn-confirm-apply"
                  onClick={handleConfirmApply}
                  disabled={isApplying}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white border border-cyan-500 shadow-md transition-all disabled:opacity-50"
                >
                  {isApplying ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Applying...
                    </>
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      Apply Fix
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Rollback Confirmation Modal */}
        {showRollbackConfirmModal && (
          <div
            className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-150"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-rollback-title"
          >
            <div
              className="relative w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-5 space-y-4 animate-in zoom-in-95 duration-150"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
                    <Undo2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 id="confirm-rollback-title" className="text-sm font-bold text-slate-100">
                      Rollback Applied Fix
                    </h3>
                    <p className="text-[11px] text-slate-400">Revert File to Original State</p>
                  </div>
                </div>
                <button
                  onClick={handleCancelConfirmRollback}
                  disabled={isRollingBack}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors disabled:opacity-50"
                  aria-label="Close rollback dialog"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {rollbackError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-300 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <span>{rollbackError}</span>
                </div>
              )}

              <div className="space-y-2.5 text-xs text-slate-300">
                <p>
                  This action will restore the target file in your local repository workspace to its exact original content prior to applying this fix.
                </p>

                <div className="space-y-1">
                  <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400">
                    Target File
                  </div>
                  <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-xl font-mono text-indigo-300 break-all select-text">
                    {fixSuggestion.file_path}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  id="btn-cancel-rollback"
                  onClick={handleCancelConfirmRollback}
                  disabled={isRollingBack}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  id="btn-confirm-rollback"
                  onClick={handleConfirmRollback}
                  disabled={isRollingBack}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white border border-amber-500 shadow-md transition-all disabled:opacity-50"
                >
                  {isRollingBack ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      Rolling back...
                    </>
                  ) : (
                    <>
                      <Undo2 className="w-3.5 h-3.5" />
                      Confirm Rollback
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
        {/* Phase 11.4B-7 Run Isolated Tests Confirmation Modal */}
        <RunIsolatedTestsModal
          isOpen={showRunTestsModal}
          onClose={() => setShowRunTestsModal(false)}
          onConfirm={handleConfirmRunTests}
          isLoading={isRunningTests}
        />

        {/* Phase 11.5B-3 Create Local Commit Confirmation Modal */}
        <CreateCommitModal
          isOpen={showCreateCommitModal}
          onClose={() => setShowCreateCommitModal(false)}
          onConfirm={handleConfirmCreateCommit}
          isLoading={isCommitting}
          filePath={fixSuggestion.file_path}
        />

        {/* Phase 11.5B-4 Push AI Fix Branch Confirmation Modal */}
        <PushBranchModal
          isOpen={showPushBranchModal}
          onClose={() => setShowPushBranchModal(false)}
          onConfirm={handleConfirmPushBranch}
          isLoading={isPushing}
          branchName={fixSuggestion.git_commit?.branch_name || 'ai-fix'}
          commitSha={fixSuggestion.git_commit?.commit_sha}
        />

        {/* Phase 11.5B-5 Create GitHub Pull Request Confirmation Modal */}
        <CreatePullRequestModal
          isOpen={showCreatePRModal}
          onClose={() => setShowCreatePRModal(false)}
          onConfirm={handleConfirmCreatePR}
          isLoading={isCreatingPR}
          headBranch={fixSuggestion.git_push?.branch_name || fixSuggestion.git_commit?.branch_name || 'ai-fix'}
          findingIssue={finding.issue}
        />
      </div>
    </div>
  );
};

