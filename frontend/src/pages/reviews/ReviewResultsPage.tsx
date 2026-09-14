import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  reviewsApi,
  CodeReview,
  ReviewFinding,
  FindingSeverity,
  FixSuggestion,
} from '../../api/reviews';
import { PerformanceTab } from './PerformanceTab';
import { RefactoringTab } from './RefactoringTab';
import { ArchitectureTab } from './ArchitectureTab';
import { FixSuggestionModal } from './FixSuggestionModal';
import { FixWorkflowStepper } from './FixWorkflowStepper';
import { CategoryStatusCard } from './CategoryStatusCard';
import type { FindingSeverityCounts } from './CategoryStatusCard';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Code2,
  ShieldAlert,
  Zap,
  Search,
  Filter,
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
  Info,
  RefreshCw,
  Wrench,
  Layers,
  Sparkles,
  ShieldCheck,
  GitCommit,
  UploadCloud,
  GitPullRequest,
  Undo2,
  Folder,
  CheckSquare,
  Square,
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

type ReviewTab = 'code' | 'security' | 'performance' | 'refactoring' | 'architecture';

// ─── Severity badge ──────────────────────────────────────────────────────────

const SEV_STYLE: Record<FindingSeverity, { color: string; bg: string; border: string }> = {
  critical: { color: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30' },
  high: { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  medium: { color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
  low: { color: 'text-sky-400', bg: 'bg-sky-500/10', border: 'border-sky-500/30' },
  info: { color: 'text-slate-400', bg: 'bg-slate-700/40', border: 'border-slate-700' },
};
const SEV_PRIORITY: Record<FindingSeverity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
};

const SeverityBadge: React.FC<{ severity: FindingSeverity }> = ({ severity }) => {
  const s = SEV_STYLE[severity] || SEV_STYLE.info;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${s.color} ${s.bg} ${s.border}`}
    >
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
};

// ─── Status badge ────────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ status: CodeReview['status'] }> = ({ status }) => {
  switch (status) {
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3 h-3" /> Completed
        </span>
      );
    case 'in_progress':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse">
          <Loader2 className="w-3 h-3 animate-spin" /> In Progress
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertCircle className="w-3 h-3" /> Failed
        </span>
      );
    case 'cancelled':
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <AlertCircle className="w-3 h-3" /> Cancelled
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-700/40 text-slate-400 border border-slate-700">
          <Clock className="w-3 h-3" /> Pending
        </span>
      );
  }
};

// ─── Finding row ─────────────────────────────────────────────────────────────

interface FindingRowProps {
  finding: ReviewFinding;
  originalIndex: number;
  displayNumber: number;
  reviewStatus: CodeReview['status'];
  isGenerating: boolean;
  isSelected?: boolean;
  onToggleSelect?: (index: number) => void;
  errorMsg?: string | null;
  onGenerateFix: (index: number, finding: ReviewFinding) => void;
  onViewFix: (index: number, finding: ReviewFinding, fix: FixSuggestion) => void;
}

const FindingRow: React.FC<FindingRowProps> = ({
  finding,
  originalIndex,
  displayNumber,
  reviewStatus,
  isGenerating,
  isSelected,
  onToggleSelect,
  errorMsg,
  onGenerateFix,
  onViewFix,
}) => {
  const [expanded, setExpanded] = useState(false);
  const fix = finding.fix_suggestion;

  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-3">
        {onToggleSelect && (
          <button
            onClick={() => onToggleSelect(originalIndex)}
            className="p-1 text-slate-500 hover:text-indigo-400 transition-colors shrink-0"
            aria-label={isSelected ? 'Deselect finding' : 'Select finding'}
          >
            {isSelected ? (
              <CheckSquare className="w-4 h-4 text-indigo-400" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </button>
        )}
        <button
          className="flex-1 flex items-start gap-3 text-left hover:opacity-90 transition-opacity"
          onClick={() => setExpanded((x) => !x)}
          aria-expanded={expanded}
        >
          <span className="text-xs text-slate-500 font-mono w-5 pt-0.5 shrink-0">{displayNumber}</span>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <SeverityBadge severity={finding.severity} />
              {finding.file_path && (
                <span className="text-[10px] text-indigo-300 font-mono bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-md truncate max-w-[280px] sm:max-w-md inline-block">
                  {finding.file_path}
                  {finding.line_number ? `:${finding.line_number}` : ''}
                </span>
              )}
              <span className="text-[10px] text-slate-500 shrink-0">
                {Math.round(finding.confidence_score * 100)}% confidence
              </span>

              {/* Fix application / decision badge if generated */}
              {fix && fix.application_status === 'applied' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-cyan-400 bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-2.5 h-2.5" /> Applied
                </span>
              )}
              {fix && fix.application_status === 'rolled_back' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
                  <Undo2 className="w-2.5 h-2.5" /> Rolled Back
                </span>
              )}
              {fix && fix.application_status === 'applied' && fix.static_verification && (
                <>
                  {fix.static_verification.status === 'passed' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                      <CheckCircle2 className="w-2.5 h-2.5" /> Static Verified
                    </span>
                  )}
                  {fix.static_verification.status === 'failed' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded-full">
                      <AlertCircle className="w-2.5 h-2.5" /> Static Verification Failed
                    </span>
                  )}
                  {fix.static_verification.status === 'unsupported' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-400 bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full">
                      <Info className="w-2.5 h-2.5" /> Verification Unsupported
                    </span>
                  )}
                  {fix.static_verification.status === 'source_changed' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
                      <AlertCircle className="w-2.5 h-2.5" /> Source Changed
                    </span>
                  )}
                </>
              )}
              {fix && fix.application_status === 'applied' && fix.test_verification && (
                <>
                  {fix.test_verification.status === 'passed' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                      <CheckCircle2 className="w-2.5 h-2.5" /> Tests Passed
                    </span>
                  )}
                  {fix.test_verification.status === 'failed' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded-full">
                      <AlertCircle className="w-2.5 h-2.5" /> Tests Failed
                    </span>
                  )}
                  {fix.test_verification.status === 'timed_out' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
                      <AlertCircle className="w-2.5 h-2.5" /> Tests Timed Out
                    </span>
                  )}
                  {fix.test_verification.status === 'sandbox_unavailable' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-300 bg-slate-800 border border-rose-500/30 px-2 py-0.5 rounded-full">
                      <AlertCircle className="w-2.5 h-2.5" /> Sandbox Unavailable
                    </span>
                  )}
                  {fix.test_verification.status === 'unsupported' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-400 bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-full">
                      <Info className="w-2.5 h-2.5" /> Tests Unsupported
                    </span>
                  )}
                  {fix.test_verification.status === 'source_changed' && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
                      <AlertCircle className="w-2.5 h-2.5" /> Source Changed
                    </span>
                  )}
                </>
              )}
              {fix && fix.application_status === 'applied' && fix.git_commit && (fix.git_commit.status === 'committed' || fix.git_commit.status === 'already_committed') && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-purple-400 bg-purple-500/10 border border-purple-500/30 px-2 py-0.5 rounded-full">
                  <GitCommit className="w-2.5 h-2.5" /> Committed (local)
                </span>
              )}
              {fix && fix.application_status === 'applied' && fix.git_push && (fix.git_push.status === 'pushed' || fix.git_push.status === 'already_pushed') && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-blue-400 bg-blue-500/10 border border-blue-500/30 px-2 py-0.5 rounded-full">
                  <UploadCloud className="w-2.5 h-2.5" /> Pushed ({fix.git_push.remote_name || 'origin'})
                </span>
              )}
              {fix && fix.git_pull_request && (fix.git_pull_request.status === 'created' || fix.git_pull_request.status === 'already_exists') && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 border border-indigo-500/30 px-2 py-0.5 rounded-full">
                  <GitPullRequest className="w-2.5 h-2.5" /> PR {fix.git_pull_request.pr_number ? `#${fix.git_pull_request.pr_number}` : 'Created'}
                </span>
              )}
              {fix && fix.application_status === 'stale' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 rounded-full">
                  <AlertCircle className="w-2.5 h-2.5" /> Stale
                </span>
              )}
              {fix && fix.application_status === 'apply_failed' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded-full">
                  <AlertCircle className="w-2.5 h-2.5" /> Apply Failed
                </span>
              )}
              {fix && !fix.application_status && fix.user_decision === 'accepted' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-2.5 h-2.5" /> Accepted
                </span>
              )}
              {fix && fix.application_status === 'not_applied' && fix.user_decision === 'accepted' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                  <CheckCircle2 className="w-2.5 h-2.5" /> Accepted
                </span>
              )}
              {fix && fix.user_decision === 'rejected' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/30 px-2 py-0.5 rounded-full">
                  <AlertCircle className="w-2.5 h-2.5" /> Rejected
                </span>
              )}
              {fix && fix.user_decision === 'pending' && (
                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-300 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded-full">
                  <Sparkles className="w-2.5 h-2.5" /> Fix Ready
                </span>
              )}
            </div>
            <div className="text-sm font-medium text-slate-200 break-words">{finding.issue}</div>
          </div>
        </button>

        {/* Action Button & Toggle */}
        <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
          {fix ? (
            <button
              id={`btn-view-fix-${originalIndex}`}
              onClick={(e) => {
                e.stopPropagation();
                onViewFix(originalIndex, finding, fix);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 transition-all shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              View Fix
            </button>
          ) : !finding.file_path || !finding.file_path.trim() ? (
            <span
              id={`badge-manual-fix-${originalIndex}`}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400 bg-slate-800/80 border border-slate-700/60 px-2.5 py-1 rounded-lg"
              title="Automated fix requires an affected file path"
            >
              Manual Fix Required
            </span>
          ) : (
            (!reviewStatus || reviewStatus.toLowerCase() === 'completed') && (
              <button
                id={`btn-generate-fix-${originalIndex}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onGenerateFix(originalIndex, finding);
                }}
                disabled={isGenerating}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-indigo-600 hover:text-white text-slate-300 border border-slate-700 hover:border-indigo-500 transition-all disabled:opacity-50"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    Auto Fix
                  </>
                )}
              </button>
            )
          )}

          <button
            onClick={() => setExpanded((x) => !x)}
            className="p-1 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition-colors"
            aria-label={expanded ? 'Collapse finding details' : 'Expand finding details'}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Inline Generation Error */}
      {errorMsg && (
        <div className="mx-4 mb-3 p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300 flex items-start gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-800/60 pt-3 bg-slate-900/60">
          {/* Fix Lifecycle Stepper */}
          {fix && (
            <FixWorkflowStepper
              finding={finding}
              fixSuggestion={fix}
              reviewStatus={reviewStatus}
              variant="compact"
            />
          )}

          {finding.explanation && (
            <div>
              <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1">Explanation</div>
              <p className="text-xs text-slate-300 leading-relaxed">{finding.explanation}</p>
            </div>
          )}
          {finding.suggested_fix && (
            <div>
              <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1">
                Suggested Fix Concept
              </div>
              <p className="text-xs text-emerald-300 leading-relaxed">{finding.suggested_fix}</p>
            </div>
          )}
          {fix && fix.static_verification && (
            <div className="pt-2 border-t border-slate-800/60">
              <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" /> Static Verification Status
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 font-medium">
                    {fix.static_verification.status === 'passed' && 'Static Verification Passed'}
                    {fix.static_verification.status === 'failed' && 'Static Verification Failed'}
                    {fix.static_verification.status === 'unsupported' && 'Static Verification Not Supported for This Language'}
                    {fix.static_verification.status === 'source_changed' && 'Source Changed After Apply'}
                    {fix.static_verification.status === 'not_run' && 'Static Verification Not Run'}
                  </span>
                  {fix.static_verification.verified_at && (
                    <span className="text-[10px] text-slate-500 font-mono">
                      {new Date(fix.static_verification.verified_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                {fix.static_verification.checks && fix.static_verification.checks.length > 0 && (
                  <div className="text-[11px] text-slate-400">
                    {fix.static_verification.checks.filter((c) => c.status === 'passed').length} / {fix.static_verification.checks.length} checks passed
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ─── Findings panel (code / security) ─────────────────────────────────────

interface FindingsPanelProps {
  findings: ReviewFinding[];
  emptyIcon: React.ReactNode;
  emptyLabel: string;
  reviewStatus: CodeReview['status'];
  generatingIndices: Record<number, boolean>;
  generationError: { index: number; message: string } | null;
  onGenerateFix: (index: number, finding: ReviewFinding) => void;
  onViewFix: (index: number, finding: ReviewFinding, fix: FixSuggestion) => void;
  onFixAllSafe?: () => Promise<void>;
  onFixBatch?: (indices: number[]) => Promise<void>;
  isBatchFixing?: boolean;
}

const FindingsPanel: React.FC<FindingsPanelProps> = ({
  findings,
  emptyIcon,
  emptyLabel,
  reviewStatus,
  generatingIndices,
  generationError,
  onGenerateFix,
  onViewFix,
  onFixAllSafe,
  onFixBatch,
  isBatchFixing = false,
}) => {
  const [search, setSearch] = useState('');
  const [sevFilter, setSevFilter] = useState<FindingSeverity | 'all'>('all');
  const [sortField, setSortField] = useState<'severity' | 'file' | 'confidence'>('severity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const [groupByFile, setGroupByFile] = useState(false);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const PAGE = 10;

  // Pair each finding with its original index in review.findings to ensure exact finding_index routing
  const indexedFindings = useMemo(() => {
    return findings.map((f, originalIndex) => ({ finding: f, originalIndex }));
  }, [findings]);

  const filtered = useMemo(() => {
    let list = [...indexedFindings];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (item) =>
          item.finding.issue.toLowerCase().includes(q) ||
          (item.finding.file_path || '').toLowerCase().includes(q) ||
          item.finding.explanation.toLowerCase().includes(q)
      );
    }
    if (sevFilter !== 'all') list = list.filter((item) => item.finding.severity === sevFilter);
    list.sort((a, b) => {
      if (sortField === 'severity') {
        const d = (SEV_PRIORITY[b.finding.severity] ?? 1) - (SEV_PRIORITY[a.finding.severity] ?? 1);
        return sortDir === 'desc' ? d : -d;
      }
      if (sortField === 'confidence') {
        const d = b.finding.confidence_score - a.finding.confidence_score;
        return sortDir === 'desc' ? d : -d;
      }
      const d = (a.finding.file_path || '').localeCompare(b.finding.file_path || '');
      return sortDir === 'desc' ? -d : d;
    });
    return list;
  }, [indexedFindings, search, sevFilter, sortField, sortDir]);

  // Grouping by file
  const groupedByFile = useMemo(() => {
    const map = new Map<string, typeof filtered>();
    filtered.forEach((item) => {
      const file = item.finding.file_path || 'Unassigned File';
      if (!map.has(file)) map.set(file, []);
      map.get(file)!.push(item);
    });
    return Array.from(map.entries());
  }, [filtered]);

  const totalPages = Math.ceil(filtered.length / PAGE);
  const paginated = filtered.slice(page * PAGE, page * PAGE + PAGE);

  const toggleSort = (f: 'severity' | 'file' | 'confidence') => {
    if (sortField === f) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortField(f);
      setSortDir('desc');
    }
    setPage(0);
  };

  const handleToggleSelect = (idx: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const handleSelectAll = () => {
    if (selectedIndices.size === filtered.length) {
      setSelectedIndices(new Set());
    } else {
      setSelectedIndices(new Set(filtered.map((item) => item.originalIndex)));
    }
  };

  const handleTriggerFixSelected = async () => {
    if (onFixBatch && selectedIndices.size > 0) {
      await onFixBatch(Array.from(selectedIndices));
      setSelectedIndices(new Set());
    }
  };

  if (!findings.length) {
    // Empty state is now handled by the parent via CategoryStatusCard
    // This fallback only fires when no CategoryStatusCard is rendered
    const isCompleted = reviewStatus && reviewStatus.toLowerCase() === 'completed';
    const isFailed = reviewStatus && reviewStatus.toLowerCase() === 'failed';
    const isCancelled = reviewStatus && reviewStatus.toLowerCase() === 'cancelled';

    return (
      <div className="flex flex-col items-center justify-center py-16 space-y-3 text-slate-400">
        <div
          className={`p-3 rounded-2xl ${
            isFailed
              ? 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
              : isCancelled
              ? 'bg-amber-500/10 border border-amber-500/20 text-amber-400'
              : 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
          }`}
        >
          {isFailed ? <AlertCircle className="w-12 h-12 text-rose-400" /> : isCancelled ? <AlertCircle className="w-12 h-12 text-amber-400" /> : emptyIcon}
        </div>
        <div className="text-center space-y-1">
          <p className="text-sm font-semibold text-slate-200">
            {isFailed ? 'Analysis unavailable due to review failure' : isCancelled ? 'Analysis not completed (Review cancelled)' : emptyLabel}
          </p>
          <p className="text-xs text-slate-400 max-w-sm">
            {isFailed
              ? 'The automated review for this category did not complete successfully.'
              : isCancelled
              ? 'This review run was cancelled before analysis could finish.'
              : 'All automated checks passed with zero issues identified in this category.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Batch Actions & Grouping Toolbar */}
      {(!reviewStatus || reviewStatus.toLowerCase() === 'completed') && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/60 border border-slate-800 rounded-xl text-xs">
          <div className="flex items-center gap-2">
            <button
              onClick={handleSelectAll}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              {selectedIndices.size > 0 && selectedIndices.size === filtered.length ? (
                <CheckSquare className="w-3.5 h-3.5 text-indigo-400" />
              ) : (
                <Square className="w-3.5 h-3.5" />
              )}
              <span>{selectedIndices.size === filtered.length ? 'Deselect All' : 'Select All'}</span>
            </button>
            {selectedIndices.size > 0 && (
              <span className="text-slate-400 font-mono">
                ({selectedIndices.size} selected)
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              id="btn-toggle-group-by-file"
              onClick={() => setGroupByFile((g) => !g)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold border transition-all ${
                groupByFile
                  ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
              }`}
            >
              <Folder className="w-3.5 h-3.5" />
              {groupByFile ? 'Flat List' : 'Group by File'}
            </button>

            {onFixBatch && (
              <button
                id="btn-fix-selected"
                onClick={handleTriggerFixSelected}
                disabled={selectedIndices.size === 0 || isBatchFixing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500 shadow-sm transition-all disabled:opacity-40"
              >
                {isBatchFixing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                Fix Selected {selectedIndices.size > 0 ? `(${selectedIndices.size})` : ''}
              </button>
            )}

            {onFixAllSafe && (
              <button
                id="btn-fix-all-safe"
                onClick={onFixAllSafe}
                disabled={isBatchFixing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-500 shadow-sm transition-all disabled:opacity-40"
              >
                {isBatchFixing ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Sparkles className="w-3.5 h-3.5" />
                )}
                Fix All Safe Issues
              </button>
            )}
          </div>
        </div>
      )}

      {/* Filters row */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search findings…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
            className="w-full pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
          <select
            value={sevFilter}
            onChange={(e) => { setSevFilter(e.target.value as FindingSeverity | 'all'); setPage(0); }}
            className="pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none"
          >
            {(['all', 'critical', 'high', 'medium', 'low', 'info'] as const).map((s) => (
              <option key={s} value={s}>
                {s === 'all' ? 'All Severities' : s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          {(['severity', 'confidence', 'file'] as const).map((f) => (
            <button
              key={f}
              onClick={() => toggleSort(f)}
              className={`flex items-center gap-1 px-3 py-2 rounded-xl text-[11px] font-medium border transition-all ${
                sortField === f
                  ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-300'
                  : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              <ArrowUpDown className="w-3 h-3" />
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Findings content: Grouped vs Paginated Flat List */}
      {groupByFile ? (
        <div className="space-y-4">
          {groupedByFile.map(([filePath, items]) => (
            <div key={filePath} className="border border-slate-800 rounded-2xl p-4 bg-slate-950/40 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                <div className="flex items-center gap-2 font-mono text-xs text-indigo-300">
                  <Folder className="w-4 h-4 text-indigo-400" />
                  <span>{filePath}</span>
                </div>
                <span className="text-[11px] text-slate-500 font-mono">
                  {items.length} {items.length === 1 ? 'issue' : 'issues'}
                </span>
              </div>
              <div className="space-y-2">
                {items.map((item, i) => (
                  <FindingRow
                    key={`${item.finding.file_path}-${item.originalIndex}`}
                    finding={item.finding}
                    originalIndex={item.originalIndex}
                    displayNumber={i + 1}
                    reviewStatus={reviewStatus}
                    isGenerating={Boolean(generatingIndices[item.originalIndex])}
                    isSelected={selectedIndices.has(item.originalIndex)}
                    onToggleSelect={handleToggleSelect}
                    errorMsg={generationError?.index === item.originalIndex ? generationError.message : null}
                    onGenerateFix={onGenerateFix}
                    onViewFix={onViewFix}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {paginated.length === 0 ? (
            <div className="flex items-center gap-2 p-4 text-xs text-slate-500">
              <Info className="w-4 h-4" /> No findings match your filters.
            </div>
          ) : (
            paginated.map((item, i) => (
              <FindingRow
                key={`${item.finding.file_path}-${item.originalIndex}`}
                finding={item.finding}
                originalIndex={item.originalIndex}
                displayNumber={page * PAGE + i + 1}
                reviewStatus={reviewStatus}
                isGenerating={Boolean(generatingIndices[item.originalIndex])}
                isSelected={selectedIndices.has(item.originalIndex)}
                onToggleSelect={handleToggleSelect}
                errorMsg={generationError?.index === item.originalIndex ? generationError.message : null}
                onGenerateFix={onGenerateFix}
                onViewFix={onViewFix}
              />
            ))
          )}
        </div>
      )}

      {/* Pagination (only for flat list) */}
      {!groupByFile && totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-slate-500">
            Page {page + 1} of {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 rounded-lg bg-slate-800 disabled:opacity-40 text-xs text-slate-300 hover:bg-slate-700 border border-slate-700 transition-all"
            >
              ← Prev
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1.5 rounded-lg bg-slate-800 disabled:opacity-40 text-xs text-slate-300 hover:bg-slate-700 border border-slate-700 transition-all"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Main ────────────────────────────────────────────────────────────────────

export const ReviewResultsPage: React.FC = () => {
  const { reviewId } = useParams<{ reviewId: string }>();
  const navigate = useNavigate();

  const [review, setReview] = useState<CodeReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<ReviewTab>('code');

  // Fix suggestion modal and loading states
  const [activeFixModal, setActiveFixModal] = useState<{
    findingIndex: number;
    finding: ReviewFinding;
    fixSuggestion: FixSuggestion;
  } | null>(null);

  const [generatingIndices, setGeneratingIndices] = useState<Record<number, boolean>>({});
  const [generationError, setGenerationError] = useState<{ index: number; message: string } | null>(null);
  const [isBatchFixing, setIsBatchFixing] = useState<boolean>(false);

  const handleFixAllSafe = async () => {
    if (!reviewId || isBatchFixing) return;
    setIsBatchFixing(true);
    try {
      const res = await reviewsApi.fixAllSafe(reviewId);
      if (res.results) {
        setReview((prev) => {
          if (!prev) return prev;
          const updatedFindings = [...(prev.findings || [])];
          res.results.forEach((r) => {
            if (r.fix_suggestion && updatedFindings[r.finding_index]) {
              updatedFindings[r.finding_index] = {
                ...updatedFindings[r.finding_index],
                fix_suggestion: r.fix_suggestion,
              };
            }
          });
          return { ...prev, findings: updatedFindings };
        });
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to auto fix safe issues');
    } finally {
      setIsBatchFixing(false);
    }
  };

  const handleFixBatch = async (indices: number[]) => {
    if (!reviewId || isBatchFixing || !indices.length) return;
    setIsBatchFixing(true);
    try {
      const res = await reviewsApi.fixBatch(reviewId, indices);
      if (res.results) {
        setReview((prev) => {
          if (!prev) return prev;
          const updatedFindings = [...(prev.findings || [])];
          res.results.forEach((r) => {
            if (r.fix_suggestion && updatedFindings[r.finding_index]) {
              updatedFindings[r.finding_index] = {
                ...updatedFindings[r.finding_index],
                fix_suggestion: r.fix_suggestion,
              };
            }
          });
          return { ...prev, findings: updatedFindings };
        });
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to auto fix selected issues');
    } finally {
      setIsBatchFixing(false);
    }
  };

  const refreshData = async (showLoading = false) => {
    if (!reviewId) return;
    if (showLoading) setLoading(true);
    try {
      const data = await reviewsApi.getReview(reviewId);
      setReview(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to load review.');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    let timer: any = null;

    const fetchReview = async (showLoading = false) => {
      if (!reviewId) return;
      if (showLoading) setLoading(true);
      try {
        const data = await reviewsApi.getReview(reviewId);
        setReview(data);
        if (data.status === 'in_progress' || data.status === 'pending') {
          timer = setTimeout(() => fetchReview(false), 2000);
        }
      } catch (e: any) {
        setError(e?.message || 'Failed to load review.');
      } finally {
        if (showLoading) setLoading(false);
      }
    };

    fetchReview(true);

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [reviewId]);

  const handleGenerateFix = async (findingIndex: number, finding: ReviewFinding) => {
    if (!reviewId) return;
    setGeneratingIndices((prev) => ({ ...prev, [findingIndex]: true }));
    setGenerationError(null);
    try {
      const res = await reviewsApi.generateFix(reviewId, findingIndex);
      const updatedFix = res.fix_suggestion;

      // Update state locally
      setReview((prev) => {
        if (!prev) return prev;
        const updatedFindings = [...(prev.findings || [])];
        if (updatedFindings[findingIndex]) {
          updatedFindings[findingIndex] = {
            ...updatedFindings[findingIndex],
            fix_suggestion: updatedFix,
          };
        }
        return { ...prev, findings: updatedFindings };
      });

      // Automatically open modal for the newly generated fix
      setActiveFixModal({
        findingIndex,
        finding,
        fixSuggestion: updatedFix,
      });
    } catch (err: any) {
      const msg = err?.message || 'Failed to generate fix suggestion. Please check API quota or try again.';
      setGenerationError({ index: findingIndex, message: msg });
    } finally {
      setGeneratingIndices((prev) => {
        const next = { ...prev };
        delete next[findingIndex];
        return next;
      });
    }
  };

  const handleViewFix = (findingIndex: number, finding: ReviewFinding, fix: FixSuggestion) => {
    setActiveFixModal({
      findingIndex,
      finding,
      fixSuggestion: fix,
    });
  };

  const handleDecisionChange = (updatedFix: FixSuggestion) => {
    const idx = updatedFix.finding_index;
    setReview((prev) => {
      if (!prev) return prev;
      const updatedFindings = [...(prev.findings || [])];
      if (updatedFindings[idx]) {
        updatedFindings[idx] = {
          ...updatedFindings[idx],
          fix_suggestion: updatedFix,
        };
      }
      return { ...prev, findings: updatedFindings };
    });

    if (activeFixModal && activeFixModal.findingIndex === idx) {
      setActiveFixModal({
        ...activeFixModal,
        fixSuggestion: updatedFix,
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24 text-slate-400">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-400 mr-2" />
        Loading review results…
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400 space-y-3">
        <AlertCircle className="w-10 h-10 text-rose-400" />
        <p className="text-sm text-slate-300">{error || 'Review not found.'}</p>
        <button
          onClick={() => navigate('/reviews')}
          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700"
        >
          ← Back to Reviews
        </button>
      </div>
    );
  }

  const codeFindings = review.findings || [];
  const securityFindings = codeFindings.filter(
    (f) => (f as any).cwe_id || (f as any).owasp_category || (f as any).attack_scenario
  );
  // Code quality = findings that are NOT security
  const cqFindings = codeFindings.filter(
    (f) => !((f as any).cwe_id || (f as any).owasp_category || (f as any).attack_scenario)
  );
  const perfFindings = review.performance_findings || [];
  const perfRecs = review.performance_recommendations || [];
  const refactoringFindings = review.refactoring_findings || [];
  const archFindings = review.architecture_findings || [];
  const catMeta = review.category_metadata;

  // Severity breakdown helpers
  const countSeverities = (items: { severity: string }[]): FindingSeverityCounts => ({
    critical: items.filter(f => f.severity === 'critical').length,
    high:     items.filter(f => f.severity === 'high').length,
    medium:   items.filter(f => f.severity === 'medium').length,
    low:      items.filter(f => f.severity === 'low').length,
    info:     items.filter(f => f.severity === 'info').length,
  });

  const cqSevCounts = countSeverities(cqFindings as any[]);
  const secSevCounts = countSeverities(securityFindings as any[]);

  const TABS: { id: ReviewTab; label: string; icon: React.ReactNode; count: number }[] = [
    { id: 'code', label: 'Code Quality', icon: <Code2 className="w-4 h-4" />, count: cqFindings.length },
    { id: 'security', label: 'Security', icon: <ShieldAlert className="w-4 h-4" />, count: securityFindings.length },
    { id: 'performance', label: 'Performance', icon: <Zap className="w-4 h-4" />, count: perfFindings.length },
    { id: 'refactoring', label: 'Refactoring', icon: <Wrench className="w-4 h-4" />, count: refactoringFindings.length },
    { id: 'architecture', label: 'Architecture & Quality', icon: <Layers className="w-4 h-4" />, count: archFindings.length },
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/reviews')}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Start Review
          </button>
          <span className="text-slate-600">/</span>
          <button
            onClick={() => navigate('/reviews/history')}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
          >
            Review History
          </button>
        </div>
        <button
          onClick={() => refreshData(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700 transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Review info banner */}
      <div className="glass-panel p-5 rounded-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-lg font-bold text-white tracking-tight">Review Results</h1>
              <StatusBadge status={review.status} />
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-slate-800 text-slate-300 border border-slate-700">
                {codeFindings.length} {codeFindings.length === 1 ? 'Finding' : 'Findings'}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">ID: {review.id}</p>
          </div>
          <div className="flex items-center gap-6 text-xs text-slate-400">
            {review.duration_ms && (
              <div className="text-center">
                <div className="text-slate-500 text-[10px] uppercase tracking-wider">Duration</div>
                <div className="text-slate-200 font-mono mt-0.5">{(review.duration_ms / 1000).toFixed(1)}s</div>
              </div>
            )}
            <div className="text-center">
              <div className="text-slate-500 text-[10px] uppercase tracking-wider">Confidence</div>
              <div className="text-slate-200 font-mono mt-0.5">
                {Math.round((review.confidence_score || 1) * 100)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-slate-500 text-[10px] uppercase tracking-wider">Created</div>
              <div className="text-slate-200 font-mono mt-0.5">
                {new Date(review.created_at).toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Failure Status Banner */}
      {review.status === 'failed' && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-xs text-rose-300 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-sm text-rose-200">Code Review Execution Failed</div>
            <p className="text-xs text-rose-300/90 leading-relaxed">
              An error occurred during automated code review analysis. Please retry the review from the Code Review page.
            </p>
          </div>
        </div>
      )}

      {/* Cancelled Status Banner */}
      {review.status === 'cancelled' && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl text-xs text-amber-300 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-sm text-amber-200">Code Review Cancelled</div>
            <p className="text-xs text-amber-300/90 leading-relaxed">
              This code review run was cancelled before completion.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-900/60 rounded-xl border border-slate-800 w-full sm:w-fit max-w-full overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === tab.id
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {tab.icon}
            {tab.label}
            <span
              className={`px-1.5 py-0.5 rounded-full text-[10px] font-mono ${
                activeTab === tab.id ? 'bg-white/20' : 'bg-slate-800'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'code' && (
          <div className="glass-panel p-6 rounded-2xl">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-4">
              <Code2 className="w-4 h-4 text-indigo-400" /> Code Quality Findings
            </h2>
            <CategoryStatusCard
              categoryKey="code_quality"
              reviewStatus={review.status}
              metadata={catMeta?.code_quality}
              findingsCount={cqFindings.length}
              severityCounts={cqSevCounts}
            />
            {cqFindings.length > 0 && (
              <FindingsPanel
                findings={cqFindings}
                emptyIcon={<CheckCircle2 className="w-12 h-12 text-emerald-400" />}
                emptyLabel="No code quality issues found."
                reviewStatus={review.status}
                generatingIndices={generatingIndices}
                generationError={generationError}
                onGenerateFix={handleGenerateFix}
                onViewFix={handleViewFix}
                onFixAllSafe={handleFixAllSafe}
                onFixBatch={handleFixBatch}
                isBatchFixing={isBatchFixing}
              />
            )}
          </div>
        )}

        {activeTab === 'security' && (
          <div className="glass-panel p-6 rounded-2xl">
            <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-4">
              <ShieldAlert className="w-4 h-4 text-rose-400" /> Security Findings
            </h2>
            <CategoryStatusCard
              categoryKey="security"
              reviewStatus={review.status}
              metadata={catMeta?.security}
              findingsCount={securityFindings.length}
              severityCounts={secSevCounts}
            />
            {securityFindings.length > 0 && (
              <FindingsPanel
                findings={securityFindings}
                emptyIcon={<CheckCircle2 className="w-12 h-12 text-emerald-400" />}
                emptyLabel="No security vulnerabilities found."
                reviewStatus={review.status}
                generatingIndices={generatingIndices}
                generationError={generationError}
                onGenerateFix={handleGenerateFix}
                onViewFix={handleViewFix}
                onFixAllSafe={handleFixAllSafe}
                onFixBatch={handleFixBatch}
                isBatchFixing={isBatchFixing}
              />
            )}
          </div>
        )}

        {activeTab === 'performance' && (
          <PerformanceTab
            findings={perfFindings}
            recommendations={perfRecs}
            performanceScore={review.performance_score ?? null}
            estimatedCpuSavings={review.estimated_cpu_savings ?? 0}
            estimatedMemorySavings={review.estimated_memory_savings ?? 0}
            estimatedLatencyImprovement={review.estimated_latency_improvement ?? 0}
            reviewStatus={review.status}
            categoryMetadata={catMeta?.performance}
          />
        )}

        {activeTab === 'refactoring' && (
          <RefactoringTab
            findings={refactoringFindings}
            overallPriority={review.refactoring_priority ?? null}
            estimatedEffort={review.estimated_refactoring_effort ?? 0}
            estimatedMaintainabilityImprovement={review.estimated_maintainability_improvement ?? 0}
            estimatedTechnicalDebtReduction={review.estimated_technical_debt_reduction ?? 0}
            estimatedComplexityReduction={review.estimated_complexity_reduction ?? 0}
            reviewStatus={review.status}
            categoryMetadata={catMeta?.refactoring}
          />
        )}

        {activeTab === 'architecture' && (
          <ArchitectureTab
            findings={archFindings}
            overallHealthScore={review.overall_health_score ?? null}
            architectureScore={review.architecture_score ?? null}
            maintainabilityScore={review.maintainability_score ?? null}
            technicalDebtScore={review.technical_debt_score ?? null}
            complexityScore={review.complexity_score ?? null}
            documentationScore={review.documentation_score ?? null}
            modularityScore={review.modularity_score ?? null}
            testabilityScore={review.testability_score ?? null}
            dependencyAnalysis={review.dependency_analysis}
            reviewStatus={review.status}
            categoryMetadata={catMeta?.architecture}
          />
        )}
      </div>

      {/* Fix Suggestion Modal */}
      {activeFixModal && (
        <FixSuggestionModal
          isOpen={Boolean(activeFixModal)}
          onClose={() => setActiveFixModal(null)}
          reviewId={review.id}
          findingIndex={activeFixModal.findingIndex}
          finding={activeFixModal.finding}
          fixSuggestion={activeFixModal.fixSuggestion}
          onDecisionChange={handleDecisionChange}
        />
      )}
    </div>
  );
};
