import React from 'react';
import {
  GitCommit,
  CheckCircle2,
  AlertCircle,
  Clock,
  Loader2,
  Info,
  ShieldCheck,
  UploadCloud,
  GitPullRequest,
  ExternalLink,
} from 'lucide-react';
import { GitCommitResult, GitPushResult, GitPullRequestResult } from '../../api/reviews';

interface CommitSectionProps {
  gitCommit?: GitCommitResult | null;
  gitPush?: GitPushResult | null;
  gitPullRequest?: GitPullRequestResult | null;
  isApplied: boolean;
  staticPassed: boolean;
  isCommitting: boolean;
  isPushing?: boolean;
  isCreatingPR?: boolean;
  onOpenConfirmModal: () => void;
  onOpenPushModal?: () => void;
  onOpenPRModal?: () => void;
  commitError?: string | null;
  pushError?: string | null;
  prError?: string | null;
}

export const CommitSection: React.FC<CommitSectionProps> = ({
  gitCommit,
  gitPush,
  gitPullRequest,
  isApplied,
  staticPassed,
  isCommitting,
  isPushing = false,
  isCreatingPR = false,
  onOpenConfirmModal,
  onOpenPushModal,
  onOpenPRModal,
  commitError,
  pushError,
  prError,
}) => {
  const isCommitted =
    gitCommit &&
    (gitCommit.status === 'committed' || gitCommit.status === 'already_committed') &&
    Boolean(gitCommit.commit_sha);

  const isPushed =
    gitPush &&
    (gitPush.status === 'pushed' || gitPush.status === 'already_pushed') &&
    Boolean(gitPush.commit_sha);

  const isPRCreated =
    gitPullRequest &&
    (gitPullRequest.status === 'created' || gitPullRequest.status === 'already_exists') &&
    Boolean(gitPullRequest.pr_url);

  const shortSha = gitCommit?.commit_sha ? gitCommit.commit_sha.slice(0, 7) : null;
  const isEligibleCommit = isApplied && staticPassed && !isCommitted;
  const isEligiblePush = isCommitted && !isPushed && Boolean(onOpenPushModal);
  const isEligiblePR = isPushed && !isPRCreated && Boolean(onOpenPRModal);

  return (
    <div
      className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-3"
      data-testid="commit-section"
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-400">
            <GitCommit className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-100 flex items-center gap-1.5 flex-wrap">
              Local Git Commit & Branch
              {isCommitted && !isPushed && !isPRCreated && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-purple-400 bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-2.5 h-2.5" /> Local Commit Created
                </span>
              )}
              {isPushed && !isPRCreated && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-2.5 h-2.5" /> Branch Pushed
                </span>
              )}
              {isPRCreated && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-2 py-0.5 rounded-full">
                  <GitPullRequest className="w-2.5 h-2.5" /> Pull Request Created
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400">
              Isolated single-file commit on dedicated AI branch
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {isEligibleCommit && (
            <button
              id="btn-open-create-commit"
              onClick={onOpenConfirmModal}
              disabled={isCommitting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white border border-purple-500 shadow-sm transition-all disabled:opacity-50"
            >
              {isCommitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Creating local commit...
                </>
              ) : (
                <>
                  <GitCommit className="w-3.5 h-3.5" /> Create Commit
                </>
              )}
            </button>
          )}

          {isEligiblePush && (
            <button
              id="btn-open-push-branch"
              onClick={onOpenPushModal}
              disabled={isPushing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white border border-blue-500 shadow-sm transition-all disabled:opacity-50"
            >
              {isPushing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Pushing branch...
                </>
              ) : (
                <>
                  <UploadCloud className="w-3.5 h-3.5" /> Push Branch
                </>
              )}
            </button>
          )}

          {isEligiblePR && (
            <button
              id="btn-open-create-pr"
              onClick={onOpenPRModal}
              disabled={isCreatingPR}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 shadow-sm transition-all disabled:opacity-50"
            >
              {isCreatingPR ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Creating pull request...
                </>
              ) : (
                <>
                  <GitPullRequest className="w-3.5 h-3.5" /> Create Pull Request
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Committed & Pushed State Details */}
      {isCommitted && (
        <div className="space-y-2.5 bg-slate-900/90 border border-purple-500/20 rounded-xl p-3 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div className="space-y-0.5">
              <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Branch
              </span>
              <div className="font-mono text-purple-300 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 break-all select-text">
                {gitCommit.branch_name || 'ai-fix'}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Commit SHA
              </span>
              <div className="font-mono text-emerald-300 bg-slate-950 px-2.5 py-1 rounded-lg border border-slate-800 select-text">
                {shortSha || '—'}
              </div>
            </div>
          </div>

          {gitCommit.committed_at && (
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
              <Clock className="w-3 h-3 text-slate-500" />
              Committed at {new Date(gitCommit.committed_at).toLocaleString()}
            </div>
          )}

          {/* Local vs Pushed vs PR status notice */}
          {!isPushed ? (
            <div className="flex items-center gap-1.5 p-2 bg-purple-950/30 border border-purple-800/40 rounded-lg text-[11px] text-purple-300">
              <ShieldCheck className="w-3.5 h-3.5 shrink-0 text-purple-400" />
              <span>Created locally. Nothing has been pushed.</span>
            </div>
          ) : !isPRCreated ? (
            <div className="space-y-1 p-2 bg-emerald-950/30 border border-emerald-800/40 rounded-lg text-[11px] text-emerald-300">
              <div className="flex items-center gap-1.5 font-semibold text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
                <span>Pushed to remote '{gitPush.remote_name || 'origin'}'.</span>
              </div>
              <p className="text-emerald-400/80 pl-5">
                Branch pushed to remote. No Pull Request has been created yet.
              </p>
            </div>
          ) : (
            <div className="space-y-2 p-2.5 bg-indigo-950/30 border border-indigo-800/40 rounded-lg text-[11px]">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-1.5 font-semibold text-indigo-300">
                  <GitPullRequest className="w-3.5 h-3.5 shrink-0 text-indigo-400" />
                  <span>
                    Pull Request {gitPullRequest.pr_number ? `#${gitPullRequest.pr_number}` : ''} Created
                  </span>
                </div>
                {gitPullRequest.pr_url && (
                  <a
                    id="link-view-pr"
                    href={gitPullRequest.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-300 hover:text-indigo-100 bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 px-2.5 py-1 rounded-lg transition-colors"
                  >
                    View Pull Request <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
              {gitPullRequest.title && (
                <div className="text-slate-300 font-medium pl-5 truncate">
                  {gitPullRequest.title}
                </div>
              )}
              <div className="text-slate-400 pl-5 text-[10px]">
                {gitPullRequest.head_branch} → {gitPullRequest.base_branch || 'main'}
              </div>
              <p className="text-indigo-300/80 pl-5 pt-0.5">
                Pull Request created. No auto-merge or approval has been performed.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Commit Error display */}
      {commitError && (
        <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-1 text-xs">
          <div className="flex items-center gap-1.5 text-rose-300 font-semibold">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            {commitError.toLowerCase().includes('source') ||
            commitError.toLowerCase().includes('modified') ||
            commitError.toLowerCase().includes('stale') ? (
              <span>Source Changed Since Apply</span>
            ) : commitError.toLowerCase().includes('not a valid git') ||
              commitError.toLowerCase().includes('not a git') ? (
              <span>Git Repository Required</span>
            ) : commitError.toLowerCase().includes('branch conflict') ||
              commitError.toLowerCase().includes('branch') ? (
              <span>Git Branch Conflict</span>
            ) : (
              <span>Local Commit Failed</span>
            )}
          </div>
          <p className="text-rose-200/90 text-[11px] pl-5.5 leading-relaxed">{commitError}</p>
        </div>
      )}

      {/* Push Error display */}
      {pushError && (
        <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-1 text-xs">
          <div className="flex items-center gap-1.5 text-rose-300 font-semibold">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            {pushError.toLowerCase().includes('no git remote') ||
            pushError.toLowerCase().includes('no remote') ? (
              <span>No Remote Configured</span>
            ) : pushError.toLowerCase().includes('mismatch') ? (
              <span>Remote Repository Mismatch</span>
            ) : pushError.toLowerCase().includes('auth') ||
              pushError.toLowerCase().includes('permission') ? (
              <span>Authentication Required</span>
            ) : pushError.toLowerCase().includes('unavailable') ||
              pushError.toLowerCase().includes('unreachable') ? (
              <span>Remote Unavailable</span>
            ) : pushError.toLowerCase().includes('rejected') ? (
              <span>Push Rejected</span>
            ) : pushError.toLowerCase().includes('state changed') ? (
              <span>Git State Changed</span>
            ) : (
              <span>Push Failed</span>
            )}
          </div>
          <p className="text-rose-200/90 text-[11px] pl-5.5 leading-relaxed">{pushError}</p>
        </div>
      )}

      {/* PR Error display */}
      {prError && (
        <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-xl space-y-1 text-xs">
          <div className="flex items-center gap-1.5 text-rose-300 font-semibold">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            {prError.toLowerCase().includes('auth') ||
            prError.toLowerCase().includes('token') ||
            prError.toLowerCase().includes('unauthorized') ? (
              <span>GitHub Authentication Required</span>
            ) : prError.toLowerCase().includes('permission') ||
              prError.toLowerCase().includes('denied') ? (
              <span>Permission Denied</span>
            ) : prError.toLowerCase().includes('rate limit') ||
              prError.toLowerCase().includes('429') ? (
              <span>Rate Limited</span>
            ) : prError.toLowerCase().includes('branch') &&
              prError.toLowerCase().includes('not found') ? (
              <span>Remote Branch Missing</span>
            ) : prError.toLowerCase().includes('already exists') ? (
              <span>Pull Request Already Exists</span>
            ) : prError.toLowerCase().includes('unavailable') ||
              prError.toLowerCase().includes('timeout') ? (
              <span>GitHub Unavailable</span>
            ) : (
              <span>Pull Request Creation Failed</span>
            )}
          </div>
          <p className="text-rose-200/90 text-[11px] pl-5.5 leading-relaxed">{prError}</p>
        </div>
      )}

      {/* Ineligible helper notices */}
      {!isCommitted && !isEligibleCommit && (
        <div className="p-2.5 bg-slate-900/60 border border-slate-800/60 rounded-lg text-[11px] text-slate-400 flex items-center gap-2">
          <Info className="w-3.5 h-3.5 text-slate-500 shrink-0" />
          {!isApplied ? (
            <span>Apply fix suggestion to enable local Git commit.</span>
          ) : !staticPassed ? (
            <span>Tier-1 static verification must pass before committing to Git.</span>
          ) : (
            <span>Commit unavailable for current fix state.</span>
          )}
        </div>
      )}
    </div>
  );
};
