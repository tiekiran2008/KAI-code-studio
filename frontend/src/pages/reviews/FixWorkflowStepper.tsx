import React from 'react';
import {
  Check,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Ban,
  FileCode,
  ShieldCheck,
  Terminal,
  GitCommit,
  UploadCloud,
  GitPullRequest,
  AlertTriangle,
} from 'lucide-react';
import {
  ReviewFinding,
  FixSuggestion,
  CodeReview,
} from '../../api/reviews';

// ─── Types ───────────────────────────────────────────────────────────────────

export type WorkflowStepId =
  | 'fix'
  | 'accept'
  | 'apply'
  | 'verify'
  | 'tests'
  | 'commit'
  | 'push'
  | 'pr';

export type WorkflowStepStatus =
  | 'pending'
  | 'current'
  | 'completed'
  | 'failed'
  | 'blocked'
  | 'rejected'
  | 'skipped';

export interface WorkflowStep {
  id: WorkflowStepId;
  label: string;
  shortLabel: string;
  description: string;
  status: WorkflowStepStatus;
  statusText: string;
  isCurrent: boolean;
}

export interface FixWorkflowStepperProps {
  finding?: ReviewFinding | null;
  fixSuggestion?: FixSuggestion | null;
  reviewStatus?: CodeReview['status'];
  variant?: 'full' | 'compact' | 'mini';
  className?: string;
}

// ─── Pure State Derivation Helper ────────────────────────────────────────────

export function deriveFixWorkflowSteps(
  finding?: ReviewFinding | null,
  fixSuggestion?: FixSuggestion | null,
  reviewStatus: CodeReview['status'] = 'completed'
): WorkflowStep[] {
  const fix = fixSuggestion || finding?.fix_suggestion || null;

  // 1. Fix Suggestion Step
  let fixStatus: WorkflowStepStatus = 'pending';
  let fixText = 'Not Generated';
  if (fix && fix.proposed_code) {
    fixStatus = 'completed';
    fixText = 'Generated';
  } else if (reviewStatus === 'completed') {
    fixStatus = 'current';
    fixText = 'Ready to Generate';
  } else {
    fixStatus = 'pending';
    fixText = 'Pending Review';
  }

  // 2. Accept Step
  let acceptStatus: WorkflowStepStatus = 'pending';
  let acceptText = 'Pending';
  if (fixStatus !== 'completed' || !fix) {
    acceptStatus = 'pending';
    acceptText = 'Waiting for Fix';
  } else if (fix.user_decision === 'accepted') {
    acceptStatus = 'completed';
    acceptText = 'Accepted';
  } else if (fix.user_decision === 'rejected') {
    acceptStatus = 'rejected';
    acceptText = 'Rejected';
  } else {
    acceptStatus = 'current';
    acceptText = 'Review Needed';
  }

  // 3. Apply Step
  let applyStatus: WorkflowStepStatus = 'pending';
  let applyText = 'Pending';
  if (acceptStatus === 'rejected') {
    applyStatus = 'blocked';
    applyText = 'Rejected';
  } else if (acceptStatus !== 'completed') {
    applyStatus = 'pending';
    applyText = 'Requires Acceptance';
  } else if (fix?.application_status === 'applied') {
    applyStatus = 'completed';
    applyText = 'Applied';
  } else if (fix?.application_status === 'stale') {
    applyStatus = 'blocked';
    applyText = 'Source Changed (Stale)';
  } else if (fix?.application_status === 'apply_failed') {
    applyStatus = 'failed';
    applyText = 'Apply Failed';
  } else if (fix?.application_status === 'rolled_back') {
    applyStatus = 'current';
    applyText = 'Rolled Back';
  } else {
    applyStatus = 'current';
    applyText = 'Ready to Apply';
  }

  // 4. Static Verification Step (Tier-1)
  let verifyStatus: WorkflowStepStatus = 'pending';
  let verifyText = 'Pending';
  if (applyStatus === 'blocked' || applyStatus === 'failed') {
    verifyStatus = 'blocked';
    verifyText = 'Apply Incomplete';
  } else if (applyStatus !== 'completed') {
    verifyStatus = 'pending';
    verifyText = 'Requires Apply';
  } else if (fix?.static_verification) {
    const s = (fix.static_verification.status || '').toLowerCase();
    if (s === 'passed') {
      verifyStatus = 'completed';
      verifyText = 'Static Passed';
    } else if (s === 'failed') {
      verifyStatus = 'failed';
      verifyText = 'Static Failed';
    } else if (s === 'source_changed') {
      verifyStatus = 'blocked';
      verifyText = 'Source Changed';
    } else if (s === 'unsupported') {
      verifyStatus = 'skipped';
      verifyText = 'Unsupported';
    } else {
      verifyStatus = 'current';
      verifyText = 'Verification Needed';
    }
  } else {
    verifyStatus = 'current';
    verifyText = 'Ready to Verify';
  }

  // 5. Isolated Container Tests Step (Tier-2)
  let testStatus: WorkflowStepStatus = 'pending';
  let testText = 'Optional / Not Run';
  const isCommitted = Boolean(
    fix?.git_commit &&
      (fix.git_commit.status === 'committed' || fix.git_commit.status === 'already_committed') &&
      fix.git_commit.commit_sha
  );

  if (verifyStatus === 'failed' || verifyStatus === 'blocked') {
    testStatus = 'blocked';
    testText = 'Verification Blocked';
  } else if (applyStatus !== 'completed') {
    testStatus = 'pending';
    testText = 'Requires Apply';
  } else if (fix?.test_verification) {
    const ts = (fix.test_verification.status || '').toLowerCase();
    if (ts === 'passed') {
      testStatus = 'completed';
      testText = 'Tests Passed';
    } else if (ts === 'failed' || ts === 'timed_out' || ts === 'execution_error') {
      testStatus = 'failed';
      testText = ts === 'timed_out' ? 'Timed Out' : 'Tests Failed';
    } else if (ts === 'sandbox_unavailable' || ts === 'source_changed') {
      testStatus = 'blocked';
      testText = ts === 'sandbox_unavailable' ? 'Offline / Unavailable' : 'Source Changed';
    } else if (ts === 'unsupported') {
      testStatus = 'skipped';
      testText = 'Tests Unsupported';
    } else {
      testStatus = isCommitted ? 'skipped' : 'current';
      testText = 'Ready to Run';
    }
  } else {
    // Tests not run
    if (isCommitted) {
      testStatus = 'skipped';
      testText = 'Skipped';
    } else if (verifyStatus === 'completed') {
      testStatus = 'current';
      testText = 'Available (Optional)';
    } else {
      testStatus = 'pending';
      testText = 'Pending Verification';
    }
  }

  // 6. Local Git Commit Step
  let commitStatus: WorkflowStepStatus = 'pending';
  let commitText = 'Pending';
  if (verifyStatus !== 'completed') {
    commitStatus = verifyStatus === 'failed' || verifyStatus === 'blocked' ? 'blocked' : 'pending';
    commitText = 'Requires Static Verify';
  } else if (isCommitted) {
    commitStatus = 'completed';
    commitText = fix?.git_commit?.commit_sha ? `Committed (${fix.git_commit.commit_sha.slice(0, 7)})` : 'Committed';
  } else if (fix?.git_commit?.status === 'stale_source' || fix?.git_commit?.status === 'dirty_conflict') {
    commitStatus = 'blocked';
    commitText = 'Git State Conflict';
  } else if (fix?.git_commit?.status === 'failed' || fix?.git_commit?.status === 'not_git_repository') {
    commitStatus = 'failed';
    commitText = 'Commit Failed';
  } else {
    commitStatus = 'current';
    commitText = 'Ready to Commit';
  }

  // 7. Push AI Branch Step
  let pushStatus: WorkflowStepStatus = 'pending';
  let pushText = 'Pending';
  const isPushed = Boolean(
    fix?.git_push &&
      (fix.git_push.status === 'pushed' || fix.git_push.status === 'already_pushed') &&
      fix.git_push.commit_sha
  );

  if (commitStatus !== 'completed') {
    pushStatus = commitStatus === 'blocked' || commitStatus === 'failed' ? 'blocked' : 'pending';
    pushText = 'Requires Local Commit';
  } else if (isPushed) {
    pushStatus = 'completed';
    pushText = `Pushed (${fix?.git_push?.remote_name || 'origin'})`;
  } else if (
    fix?.git_push?.status === 'auth_required' ||
    fix?.git_push?.status === 'remote_mismatch' ||
    fix?.git_push?.status === 'git_state_changed'
  ) {
    pushStatus = 'blocked';
    pushText = fix?.git_push?.status === 'auth_required' ? 'Auth Required' : 'Remote Conflict';
  } else if (
    fix?.git_push?.status === 'no_remote' ||
    fix?.git_push?.status === 'push_rejected' ||
    fix?.git_push?.status === 'remote_unavailable' ||
    fix?.git_push?.status === 'failed'
  ) {
    pushStatus = 'failed';
    pushText = 'Push Failed';
  } else {
    pushStatus = 'current';
    pushText = 'Ready to Push';
  }

  // 8. Pull Request Step
  let prStatus: WorkflowStepStatus = 'pending';
  let prText = 'Pending';
  const isPRCreated = Boolean(
    fix?.git_pull_request &&
      (fix.git_pull_request.status === 'created' || fix.git_pull_request.status === 'already_exists') &&
      fix.git_pull_request.pr_url
  );

  if (pushStatus !== 'completed') {
    prStatus = pushStatus === 'blocked' || pushStatus === 'failed' ? 'blocked' : 'pending';
    prText = 'Requires Push';
  } else if (isPRCreated) {
    prStatus = 'completed';
    prText = fix?.git_pull_request?.pr_number ? `PR #${fix.git_pull_request.pr_number} Created` : 'PR Created';
  } else if (
    fix?.git_pull_request?.status === 'auth_required' ||
    fix?.git_pull_request?.status === 'permission_denied' ||
    fix?.git_pull_request?.status === 'git_state_changed' ||
    fix?.git_pull_request?.status === 'rate_limited'
  ) {
    prStatus = 'blocked';
    prText = fix?.git_pull_request?.status === 'rate_limited' ? 'Rate Limited' : 'Auth Required';
  } else if (
    fix?.git_pull_request?.status === 'remote_branch_missing' ||
    fix?.git_pull_request?.status === 'unavailable' ||
    fix?.git_pull_request?.status === 'failed'
  ) {
    prStatus = 'failed';
    prText = 'PR Creation Failed';
  } else {
    prStatus = 'current';
    prText = 'Ready for PR';
  }

  const steps: WorkflowStep[] = [
    {
      id: 'fix',
      label: '1. Fix',
      shortLabel: 'Fix',
      description: 'AI-generated fix suggestion',
      status: fixStatus,
      statusText: fixText,
      isCurrent: fixStatus === 'current',
    },
    {
      id: 'accept',
      label: '2. Accept',
      shortLabel: 'Accept',
      description: 'Review and approve fix concept',
      status: acceptStatus,
      statusText: acceptText,
      isCurrent: acceptStatus === 'current',
    },
    {
      id: 'apply',
      label: '3. Apply',
      shortLabel: 'Apply',
      description: 'Write fix patch to local workspace file',
      status: applyStatus,
      statusText: applyText,
      isCurrent: applyStatus === 'current',
    },
    {
      id: 'verify',
      label: '4. Verify',
      shortLabel: 'Verify',
      description: 'Perform static syntax, AST, and import checks',
      status: verifyStatus,
      statusText: verifyText,
      isCurrent: verifyStatus === 'current',
    },
    {
      id: 'tests',
      label: '5. Tests',
      shortLabel: 'Tests',
      description: 'Run isolated pytest container verification',
      status: testStatus,
      statusText: testText,
      isCurrent: testStatus === 'current',
    },
    {
      id: 'commit',
      label: '6. Commit',
      shortLabel: 'Commit',
      description: 'Create local Git commit on dedicated AI branch',
      status: commitStatus,
      statusText: commitText,
      isCurrent: commitStatus === 'current',
    },
    {
      id: 'push',
      label: '7. Push',
      shortLabel: 'Push',
      description: 'Push dedicated AI fix branch to remote repository',
      status: pushStatus,
      statusText: pushText,
      isCurrent: pushStatus === 'current',
    },
    {
      id: 'pr',
      label: '8. PR',
      shortLabel: 'PR',
      description: 'Open GitHub Pull Request for team review (no auto-merge)',
      status: prStatus,
      statusText: prText,
      isCurrent: prStatus === 'current',
    },
  ];

  return steps;
}

// ─── Visual Presentation ─────────────────────────────────────────────────────

const STATUS_ICONS: Record<WorkflowStepStatus, React.ReactNode> = {
  completed: <Check className="w-3 h-3 text-emerald-400 stroke-[3]" />,
  current: <Sparkles className="w-3 h-3 text-indigo-400 animate-pulse" />,
  failed: <AlertCircle className="w-3 h-3 text-rose-400 stroke-[2.5]" />,
  blocked: <AlertTriangle className="w-3 h-3 text-amber-400 stroke-[2.5]" />,
  rejected: <Ban className="w-3 h-3 text-rose-400 stroke-[2.5]" />,
  skipped: <Clock className="w-3 h-3 text-slate-500" />,
  pending: <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />,
};

const STEP_ICONS: Record<WorkflowStepId, React.ReactNode> = {
  fix: <Sparkles className="w-3.5 h-3.5" />,
  accept: <CheckCircle2 className="w-3.5 h-3.5" />,
  apply: <FileCode className="w-3.5 h-3.5" />,
  verify: <ShieldCheck className="w-3.5 h-3.5" />,
  tests: <Terminal className="w-3.5 h-3.5" />,
  commit: <GitCommit className="w-3.5 h-3.5" />,
  push: <UploadCloud className="w-3.5 h-3.5" />,
  pr: <GitPullRequest className="w-3.5 h-3.5" />,
};

const STATUS_BADGE_STYLES: Record<WorkflowStepStatus, { bg: string; text: string; border: string }> = {
  completed: { bg: 'bg-emerald-500/15', text: 'text-emerald-300', border: 'border-emerald-500/30' },
  current: { bg: 'bg-indigo-500/20', text: 'text-indigo-200', border: 'border-indigo-500/50 shadow-sm shadow-indigo-500/20' },
  failed: { bg: 'bg-rose-500/15', text: 'text-rose-300', border: 'border-rose-500/30' },
  blocked: { bg: 'bg-amber-500/15', text: 'text-amber-300', border: 'border-amber-500/30' },
  rejected: { bg: 'bg-rose-500/15', text: 'text-rose-300', border: 'border-rose-500/30' },
  skipped: { bg: 'bg-slate-800/60', text: 'text-slate-400', border: 'border-slate-700/60' },
  pending: { bg: 'bg-slate-900/40', text: 'text-slate-500', border: 'border-slate-800' },
};

export const FixWorkflowStepper: React.FC<FixWorkflowStepperProps> = ({
  finding,
  fixSuggestion,
  reviewStatus = 'completed',
  variant = 'full',
  className = '',
}) => {
  const steps = deriveFixWorkflowSteps(finding, fixSuggestion, reviewStatus);
  const isFinalPRCreated = steps.find((s) => s.id === 'pr')?.status === 'completed';

  if (variant === 'mini') {
    return (
      <div
        className={`flex items-center gap-1 overflow-x-auto py-1 ${className}`}
        data-testid="fix-workflow-stepper-mini"
        role="list"
        aria-label="Workflow progress steps"
      >
        {steps.map((step, idx) => {
          const style = STATUS_BADGE_STYLES[step.status];
          return (
            <div
              key={step.id}
              role="listitem"
              data-testid={`stepper-step-${step.id}`}
              aria-current={step.isCurrent ? 'step' : undefined}
              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${style.bg} ${style.text} ${style.border}`}
              title={`${step.label}: ${step.statusText} — ${step.description}`}
            >
              <span className="shrink-0">{STATUS_ICONS[step.status]}</span>
              <span className="truncate">{step.shortLabel}</span>
              {idx < steps.length - 1 && <span className="text-slate-600 select-none ml-0.5">›</span>}
            </div>
          );
        })}
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div
        className={`bg-slate-950/70 border border-slate-800 rounded-xl p-2.5 space-y-2 ${className}`}
        data-testid="fix-workflow-stepper-compact"
        role="region"
        aria-label="Fix Lifecycle Workflow Stepper"
      >
        <div className="flex items-center justify-between text-[11px] font-medium text-slate-400 px-1">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            AI Fix Lifecycle
          </span>
          {isFinalPRCreated ? (
            <span className="text-indigo-300 font-semibold flex items-center gap-1">
              <GitPullRequest className="w-3 h-3" /> Pull Request Created
            </span>
          ) : (
            <span className="text-slate-500 font-mono text-[10px]">
              {steps.filter((s) => s.status === 'completed').length} / {steps.length} Steps Complete
            </span>
          )}
        </div>

        <div
          className="grid grid-cols-4 sm:grid-cols-8 gap-1.5"
          role="list"
          aria-label="Workflow progress steps"
        >
          {steps.map((step) => {
            const style = STATUS_BADGE_STYLES[step.status];
            return (
              <div
                key={step.id}
                role="listitem"
                data-testid={`stepper-step-${step.id}`}
                aria-current={step.isCurrent ? 'step' : undefined}
                className={`flex flex-col items-center justify-center p-1.5 rounded-lg border text-center transition-all ${style.bg} ${style.border}`}
                title={`${step.label}: ${step.statusText} — ${step.description}`}
              >
                <div className="flex items-center gap-1 mb-0.5">
                  <span className="shrink-0">{STATUS_ICONS[step.status]}</span>
                  <span className={`text-[10px] font-bold ${style.text}`}>{step.shortLabel}</span>
                </div>
                <span
                  data-testid={`stepper-step-status-${step.id}`}
                  className="text-[9px] text-slate-400 font-mono truncate max-w-full px-0.5"
                >
                  {step.statusText}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Full Variant (Used in Modals and detailed sections)
  return (
    <div
      className={`bg-slate-950/80 border border-slate-800 rounded-xl p-3.5 space-y-3 ${className}`}
      data-testid="fix-workflow-stepper"
      role="region"
      aria-label="Fix Lifecycle Workflow Stepper"
    >
      {/* Header Info */}
      <div className="flex items-center justify-between gap-2 flex-wrap pb-2 border-b border-slate-800/80 text-xs">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="font-bold text-slate-100">AI Fix & Pull Request Workflow</span>
            <span className="text-[10px] text-slate-400 ml-2">
              (Linear Ordered Lifecycle)
            </span>
          </div>
        </div>

        {isFinalPRCreated ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
            <GitPullRequest className="w-3.5 h-3.5" /> Pull Request Created
          </span>
        ) : (
          <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded-md border border-slate-800">
            {steps.filter((s) => s.status === 'completed').length} / {steps.length} Completed
          </span>
        )}
      </div>

      {/* Responsive Step Grid */}
      <div
        className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2"
        role="list"
        aria-label="Workflow progress steps"
      >
        {steps.map((step) => {
          const style = STATUS_BADGE_STYLES[step.status];
          return (
            <div
              key={step.id}
              role="listitem"
              data-testid={`stepper-step-${step.id}`}
              aria-current={step.isCurrent ? 'step' : undefined}
              className={`flex flex-col justify-between p-2 rounded-xl border transition-all ${style.bg} ${style.border}`}
            >
              <div className="flex items-center justify-between gap-1 mb-1">
                <div className="flex items-center gap-1 text-[11px] font-bold text-slate-200">
                  <span className="text-slate-400">{STEP_ICONS[step.id]}</span>
                  <span>{step.shortLabel}</span>
                </div>
                <span className="shrink-0">{STATUS_ICONS[step.status]}</span>
              </div>

              <div className="space-y-0.5">
                <div
                  data-testid={`stepper-step-status-${step.id}`}
                  className={`text-[10px] font-semibold truncate ${style.text}`}
                  title={step.statusText}
                >
                  {step.statusText}
                </div>
                <div className="text-[9px] text-slate-500 leading-tight line-clamp-2" title={step.description}>
                  {step.description}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
