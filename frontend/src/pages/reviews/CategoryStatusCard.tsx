/**
 * CategoryStatusCard
 * ==================
 * Renders one of 5 explicit analysis states for a review category:
 *   SUCCESS_WITH_FINDINGS  – compact severity-distribution header above the findings list
 *   SUCCESS_ZERO_FINDINGS  – professional "Analysis Passed" card with real metadata
 *   NOT_EVALUATED          – category was disabled or not run
 *   FAILED                 – agent error during analysis
 *   LOADING                – review still in progress (rare, defensive)
 *
 * No fake / hardcoded values. Metadata displayed only when the backend actually measured it.
 */

import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Minus,
  Loader2,
  Clock,
  FileCode2,
  Shield,
  Zap,
  Wrench,
  Layers,
} from 'lucide-react';
import type { CategoryAnalysisMetadata, FindingSeverity } from '../../api/reviews';

// ─── Types ──────────────────────────────────────────────────────────────────

export type CategoryKey = 'code_quality' | 'security' | 'performance' | 'refactoring' | 'architecture';

export type AnalysisState =
  | 'SUCCESS_WITH_FINDINGS'
  | 'SUCCESS_ZERO_FINDINGS'
  | 'NOT_EVALUATED'
  | 'FAILED'
  | 'LOADING';

export interface FindingSeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info?: number;
}

interface CategoryStatusCardProps {
  categoryKey: CategoryKey;
  /** Actual review overall status from backend */
  reviewStatus: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  /** Per-category metadata from backend – undefined when not available (old reviews) */
  metadata?: CategoryAnalysisMetadata;
  /** Actual finding count in this category */
  findingsCount: number;
  /** Severity breakdown of findings (used in findings header only) */
  severityCounts?: FindingSeverityCounts;
}

// ─── Config per category ─────────────────────────────────────────────────────

const CATEGORY_CONFIG: Record<CategoryKey, {
  label: string;
  icon: React.ReactNode;
  passedStatusLabel: string;
  passedDescription: string;
  notEvaluatedDescription: string;
}> = {
  code_quality: {
    label: 'Code Quality',
    icon: <FileCode2 className="w-5 h-5" />,
    passedStatusLabel: 'PASSED',
    passedDescription: 'No significant code-quality issues were detected in the analyzed codebase.',
    notEvaluatedDescription: 'Code quality analysis was not enabled for this review run.',
  },
  security: {
    label: 'Security',
    icon: <Shield className="w-5 h-5" />,
    passedStatusLabel: 'CLEAN',
    passedDescription: 'No security vulnerabilities were detected in the analyzed code.',
    notEvaluatedDescription: 'Security analysis was not enabled for this review run.',
  },
  performance: {
    label: 'Performance',
    icon: <Zap className="w-5 h-5" />,
    passedStatusLabel: 'HEALTHY',
    passedDescription: 'No significant performance bottlenecks were detected in the analyzed code.',
    notEvaluatedDescription: 'Performance analysis was not enabled for this review run.',
  },
  refactoring: {
    label: 'Refactoring',
    icon: <Wrench className="w-5 h-5" />,
    passedStatusLabel: 'OPTIMIZED',
    passedDescription: 'No important refactoring opportunities were identified. The codebase is well-structured.',
    notEvaluatedDescription: 'Refactoring analysis was not enabled for this review run.',
  },
  architecture: {
    label: 'Architecture',
    icon: <Layers className="w-5 h-5" />,
    passedStatusLabel: 'SOUND',
    passedDescription: 'No major architectural issues were detected. The codebase maintains high architectural integrity.',
    notEvaluatedDescription: 'Architecture analysis was not enabled for this review run.',
  },
};

// ─── Determine analysis state ────────────────────────────────────────────────

function deriveState(
  reviewStatus: CategoryStatusCardProps['reviewStatus'],
  metadata: CategoryAnalysisMetadata | undefined,
  findingsCount: number,
): AnalysisState {
  if (reviewStatus === 'in_progress' || reviewStatus === 'pending') return 'LOADING';
  if (reviewStatus === 'failed' || reviewStatus === 'cancelled') {
    if (metadata?.status === 'not_evaluated') return 'NOT_EVALUATED';
    return 'FAILED';
  }
  // reviewStatus === 'completed'
  if (!metadata) {
    // Old review without metadata – fall back to simple array-count logic
    return findingsCount > 0 ? 'SUCCESS_WITH_FINDINGS' : 'SUCCESS_ZERO_FINDINGS';
  }
  if (metadata.status === 'not_evaluated') return 'NOT_EVALUATED';
  if (metadata.status === 'failed') return 'FAILED';
  // status === 'completed'
  return findingsCount > 0 ? 'SUCCESS_WITH_FINDINGS' : 'SUCCESS_ZERO_FINDINGS';
}

// ─── Severity chip ───────────────────────────────────────────────────────────

const SEV_CHIPS: { key: FindingSeverity; label: string; colorClass: string }[] = [
  { key: 'critical', label: 'Critical', colorClass: 'text-rose-400 bg-rose-500/10 border-rose-500/25' },
  { key: 'high',     label: 'High',     colorClass: 'text-orange-400 bg-orange-500/10 border-orange-500/25' },
  { key: 'medium',   label: 'Medium',   colorClass: 'text-amber-400 bg-amber-500/10 border-amber-500/25' },
  { key: 'low',      label: 'Low',      colorClass: 'text-sky-400 bg-sky-500/10 border-sky-500/25' },
];

const SeverityChip: React.FC<{ label: string; count: number; colorClass: string }> = ({
  label, count, colorClass,
}) => (
  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${colorClass}`}>
    <span className="font-mono">{count}</span>
    <span className="opacity-80">{label}</span>
  </span>
);

// ─── MetaChip ────────────────────────────────────────────────────────────────

const MetaChip: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({
  icon, label, value,
}) => (
  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800/70 border border-slate-700/60 text-xs">
    <span className="text-slate-500">{icon}</span>
    <span className="text-slate-400">{label}</span>
    <span className="text-slate-200 font-mono font-medium">{value}</span>
  </div>
);

// ─── Main Component ──────────────────────────────────────────────────────────

export const CategoryStatusCard: React.FC<CategoryStatusCardProps> = ({
  categoryKey,
  reviewStatus,
  metadata,
  findingsCount,
  severityCounts,
}) => {
  const cfg = CATEGORY_CONFIG[categoryKey];
  const state = deriveState(reviewStatus, metadata, findingsCount);

  // ── LOADING ─────────────────────────────────────────────────────────────
  if (state === 'LOADING') {
    return (
      <div className="flex items-center gap-3 p-4 rounded-2xl border border-slate-700/60 bg-slate-900/40 text-slate-400 text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-indigo-400 shrink-0" />
        <span>Analysing {cfg.label.toLowerCase()}&hellip;</span>
      </div>
    );
  }

  // ── NOT_EVALUATED ────────────────────────────────────────────────────────
  if (state === 'NOT_EVALUATED') {
    return (
      <div
        data-testid={`category-not-evaluated-${categoryKey}`}
        className="flex items-start gap-4 p-5 rounded-2xl border border-slate-700/40 bg-slate-900/30"
      >
        <div className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/50 text-slate-500 shrink-0">
          <Minus className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-400">Not Evaluated</p>
          <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{cfg.notEvaluatedDescription}</p>
        </div>
      </div>
    );
  }

  // ── FAILED ───────────────────────────────────────────────────────────────
  if (state === 'FAILED') {
    return (
      <div
        data-testid={`category-failed-${categoryKey}`}
        className="flex items-start gap-4 p-5 rounded-2xl border border-rose-500/25 bg-rose-500/5"
      >
        <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-400 shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm font-semibold text-rose-300">Analysis Failed</p>
          <p className="text-xs text-rose-400/70 mt-0.5 leading-relaxed">
            The automated analysis for this category did not complete successfully.
            Review the overall status or retry the code review.
          </p>
        </div>
      </div>
    );
  }

  // ── SUCCESS_WITH_FINDINGS ────────────────────────────────────────────────
  // Compact header shown above the findings list
  if (state === 'SUCCESS_WITH_FINDINGS') {
    return (
      <div
        data-testid={`category-findings-header-${categoryKey}`}
        className="flex flex-wrap items-center justify-between gap-3 p-4 mb-4 rounded-xl border border-slate-700/50 bg-slate-900/40"
      >
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 shrink-0">
            {cfg.icon}
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">{cfg.label} Analysis</p>
            <p className="text-xs text-slate-500">
              {findingsCount} {findingsCount === 1 ? 'finding' : 'findings'} detected
            </p>
          </div>
        </div>
        {severityCounts && (
          <div className="flex flex-wrap gap-1.5">
            {SEV_CHIPS.map(({ key, label, colorClass }) =>
              severityCounts[key] > 0 ? (
                <SeverityChip key={key} label={label} count={severityCounts[key]} colorClass={colorClass} />
              ) : null
            )}
          </div>
        )}
      </div>
    );
  }

  // ── SUCCESS_ZERO_FINDINGS ────────────────────────────────────────────────
  const evaluatedAt = metadata?.evaluated_at
    ? (() => { try { return new Date(metadata.evaluated_at as string).toLocaleString(); } catch { return null; } })()
    : null;

  return (
    <div
      data-testid={`category-passed-${categoryKey}`}
      className="flex flex-col sm:flex-row sm:items-start gap-5 p-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/5"
    >
      {/* Check icon */}
      <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0 self-start">
        <CheckCircle2 className="w-7 h-7" />
      </div>

      <div className="flex-1 min-w-0 space-y-4">
        {/* Title row */}
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-sm font-bold text-emerald-300">
            &#10003; {cfg.label} Analysis Passed
          </h3>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wider border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
            {cfg.passedStatusLabel}
          </span>
        </div>

        {/* Description */}
        <p className="text-xs text-slate-400 leading-relaxed">{cfg.passedDescription}</p>

        {/* Zero-count severity summary */}
        <div className="flex flex-wrap gap-2">
          {SEV_CHIPS.map(({ key, label, colorClass }) => (
            <SeverityChip key={key} label={label} count={0} colorClass={colorClass} />
          ))}
          <SeverityChip
            label="Total Findings"
            count={0}
            colorClass="text-slate-400 bg-slate-700/30 border-slate-700/50"
          />
        </div>

        {/* Real metadata chips — only if the backend measured them */}
        {(metadata?.files_analyzed != null || metadata?.duration_ms != null || evaluatedAt) && (
          <div className="flex flex-wrap gap-2">
            {metadata?.files_analyzed != null && (
              <MetaChip
                icon={<FileCode2 className="w-3.5 h-3.5" />}
                label="Files analyzed"
                value={String(metadata.files_analyzed)}
              />
            )}
            {metadata?.duration_ms != null && (
              <MetaChip
                icon={<Clock className="w-3.5 h-3.5" />}
                label="Duration"
                value={`${(metadata.duration_ms / 1000).toFixed(1)}s`}
              />
            )}
            {evaluatedAt && (
              <MetaChip
                icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                label="Evaluated at"
                value={evaluatedAt}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
