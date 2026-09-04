import React, { useState, useMemo } from 'react';
import {
  RefactoringFinding,
  FindingSeverity,
  RefactoringCategory,
} from '../../api/reviews';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
  Info,
  CheckCircle2,
  Wrench,
  TrendingUp,
  Clock,
  AlertTriangle,
  Zap,
  BarChart2,
} from 'lucide-react';

// ─── Constants ─────────────────────────────────────────────────────────────────

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

const CATEGORY_LABELS: Record<string, string> = {
  complexity: 'Complexity',
  duplication: 'Duplication',
  naming: 'Naming',
  coupling: 'Coupling',
  cohesion: 'Cohesion',
  solid: 'SOLID',
  patterns: 'Design Patterns',
  dead_code: 'Dead Code',
  structure: 'Structure',
  error_handling: 'Error Handling',
  async: 'Async',
  god_object: 'God Object',
  feature_envy: 'Feature Envy',
  smells: 'Code Smells',
};

const ALL_CATEGORIES: RefactoringCategory[] = [
  'complexity', 'duplication', 'naming', 'coupling', 'cohesion', 'solid',
  'patterns', 'dead_code', 'structure', 'error_handling', 'async', 'god_object', 'feature_envy', 'smells',
];

// ─── Sub-components ────────────────────────────────────────────────────────────

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

const CategoryBadge: React.FC<{ category: string }> = ({ category }) => (
  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-500/10 text-violet-300 border border-violet-500/20">
    {CATEGORY_LABELS[category] || category}
  </span>
);

// ─── Maintainability Score Ring ─────────────────────────────────────────────────

const MaintainabilityRing: React.FC<{ score: number }> = ({ score }) => {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;
  const color =
    score >= 70 ? 'stroke-emerald-400' : score >= 40 ? 'stroke-amber-400' : 'stroke-rose-400';
  const textColor =
    score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-rose-400';

  return (
    <div className="relative w-32 h-32">
      <svg className="transform -rotate-90 w-32 h-32" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="currentColor" strokeWidth="8" className="text-slate-800" />
        <circle
          cx="60" cy="60" r={radius} fill="none" strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${color} transition-all duration-700 ease-out`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${textColor}`}>+{score.toFixed(0)}%</span>
        <span className="text-[10px] text-slate-400 mt-0.5">Maintainability</span>
      </div>
    </div>
  );
};

// ─── Finding Row ────────────────────────────────────────────────────────────────

const RefactoringRow: React.FC<{ finding: RefactoringFinding; index: number }> = ({ finding, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-slate-800/40 transition-colors"
        onClick={() => setExpanded((x) => !x)}
        aria-expanded={expanded}
      >
        <span className="text-xs text-slate-500 font-mono w-5 pt-0.5 shrink-0">{index + 1}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <SeverityBadge severity={finding.priority} />
            <CategoryBadge category={finding.category} />
            {finding.file_path && (
              <span className="text-[10px] text-indigo-300 font-mono bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-md">
                {finding.file_path}
                {finding.line_number ? `:${finding.line_number}` : ''}
              </span>
            )}
            <span className="text-[10px] text-slate-500 ml-auto">
              {Math.round(finding.confidence_score * 100)}% confidence
            </span>
          </div>
          <div className="text-sm font-medium text-slate-200 truncate">
            <span className="text-violet-300 font-semibold mr-1.5">[{finding.refactoring_type}]</span>
            {finding.explanation.slice(0, 120)}
            {finding.explanation.length > 120 ? '…' : ''}
          </div>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-slate-800/60 pt-3 bg-slate-900/30">
          {/* Explanation */}
          <div>
            <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1">Explanation</div>
            <p className="text-xs text-slate-300 leading-relaxed">{finding.explanation}</p>
          </div>

          {/* Current Problem & Suggested Refactoring */}
          {(finding.current_problem || finding.suggested_refactoring) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {finding.current_problem && (
                <div>
                  <div className="text-[11px] text-rose-400 uppercase tracking-wider font-semibold mb-1">Current Problem</div>
                  <p className="text-xs text-rose-300/90 leading-relaxed bg-rose-500/5 border border-rose-500/20 rounded-lg p-2.5">
                    {finding.current_problem}
                  </p>
                </div>
              )}
              {finding.suggested_refactoring && (
                <div>
                  <div className="text-[11px] text-emerald-400 uppercase tracking-wider font-semibold mb-1">Suggested Refactoring</div>
                  <p className="text-xs text-emerald-300/90 leading-relaxed bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-2.5">
                    {finding.suggested_refactoring}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Before / After Code Preview */}
          {(finding.before_preview || finding.after_preview) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {finding.before_preview && (
                <div>
                  <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold mb-1">Before Preview</div>
                  <pre className="text-[11px] text-slate-300 bg-slate-950 border border-slate-800 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                    {finding.before_preview}
                  </pre>
                </div>
              )}
              {finding.after_preview && (
                <div>
                  <div className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold mb-1">After Preview</div>
                  <pre className="text-[11px] text-slate-300 bg-slate-950 border border-slate-800 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                    {finding.after_preview}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Benefits & Risks */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {finding.benefits?.length > 0 && (
              <div>
                <div className="text-[11px] text-emerald-400 uppercase tracking-wider font-semibold mb-1.5 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> Expected Benefits
                </div>
                <ul className="space-y-1">
                  {finding.benefits.map((b, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-slate-300">
                      <CheckCircle2 className="w-3 h-3 text-emerald-500 mt-0.5 shrink-0" />
                      {b}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {finding.risks?.length > 0 && (
              <div>
                <div className="text-[11px] text-amber-400 uppercase tracking-wider font-semibold mb-1.5 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Potential Risks
                </div>
                <ul className="space-y-1">
                  {finding.risks.map((r, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-slate-300">
                      <AlertTriangle className="w-3 h-3 text-amber-500 mt-0.5 shrink-0" />
                      {r}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Effort & Metadata */}
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" /> Est. Effort: <span className="text-slate-200 font-mono">{finding.estimated_effort_hours}h</span>
            </div>
            <div className="flex items-center gap-1">
              <Zap className="w-3 h-3 text-amber-400" /> Confidence: <span className="text-slate-200 font-mono">{Math.round(finding.confidence_score * 100)}%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Props ──────────────────────────────────────────────────────────────────────

interface RefactoringTabProps {
  findings: RefactoringFinding[];
  overallPriority: FindingSeverity | null;
  estimatedEffort: number;
  estimatedMaintainabilityImprovement: number;
  estimatedTechnicalDebtReduction?: number;
  estimatedComplexityReduction?: number;
}

// ─── Main Component ─────────────────────────────────────────────────────────────

export const RefactoringTab: React.FC<RefactoringTabProps> = ({
  findings,
  overallPriority: _overallPriority,
  estimatedEffort,
  estimatedMaintainabilityImprovement,
  estimatedTechnicalDebtReduction = 0,
  estimatedComplexityReduction = 0,
}) => {
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<FindingSeverity | 'all'>('all');
  const [categoryFilter, setCategoryFilter] = useState<RefactoringCategory | 'all'>('all');
  const [sortField, setSortField] = useState<'priority' | 'effort' | 'confidence'>('priority');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 10;

  // Derived counts for summary cards
  const priorityCounts = useMemo(() => {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    findings.forEach((f) => { counts[f.priority] = (counts[f.priority] || 0) + 1; });
    return counts;
  }, [findings]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    findings.forEach((f) => { counts[f.category] = (counts[f.category] || 0) + 1; });
    return counts;
  }, [findings]);

  // Filter + sort
  const filtered = useMemo(() => {
    let list = [...findings];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (f) =>
          f.refactoring_type.toLowerCase().includes(q) ||
          f.explanation.toLowerCase().includes(q) ||
          (f.file_path || '').toLowerCase().includes(q) ||
          f.category.toLowerCase().includes(q)
      );
    }
    if (priorityFilter !== 'all') list = list.filter((f) => f.priority === priorityFilter);
    if (categoryFilter !== 'all') list = list.filter((f) => f.category === categoryFilter);
    list.sort((a, b) => {
      if (sortField === 'priority') {
        const d = (SEV_PRIORITY[b.priority] ?? 1) - (SEV_PRIORITY[a.priority] ?? 1);
        return sortDir === 'desc' ? d : -d;
      }
      if (sortField === 'effort') {
        const d = b.estimated_effort_hours - a.estimated_effort_hours;
        return sortDir === 'desc' ? d : -d;
      }
      // confidence
      const d = b.confidence_score - a.confidence_score;
      return sortDir === 'desc' ? d : -d;
    });
    return list;
  }, [findings, search, priorityFilter, categoryFilter, sortField, sortDir]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const toggleSort = (f: 'priority' | 'effort' | 'confidence') => {
    if (sortField === f) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortField(f);
      setSortDir('desc');
    }
    setPage(0);
  };

  // Empty state
  if (!findings.length) {
    return (
      <div className="glass-panel p-6 rounded-2xl">
        <div className="flex flex-col items-center justify-center py-20 space-y-3 text-slate-400">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 opacity-50" />
          <p className="text-sm font-medium text-slate-300">No refactoring suggestions found.</p>
          <p className="text-xs text-slate-500">The code looks well-structured.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Metrics Dashboard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Maintainability Improvement Ring */}
        <div className="glass-panel p-5 rounded-2xl flex flex-col items-center justify-center col-span-1 sm:col-span-2 lg:col-span-1">
          <MaintainabilityRing score={estimatedMaintainabilityImprovement} />
        </div>

        {/* Total Suggestions */}
        <div className="glass-panel p-5 rounded-2xl">
          <div className="flex items-center gap-2 mb-3">
            <Wrench className="w-4 h-4 text-violet-400" />
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Suggestions</span>
          </div>
          <div className="text-2xl font-bold text-white">{findings.length}</div>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {priorityCounts.critical > 0 && <span className="text-[10px] text-rose-400">⬤ {priorityCounts.critical} Critical</span>}
            {priorityCounts.high > 0 && <span className="text-[10px] text-orange-400">⬤ {priorityCounts.high} High</span>}
            {priorityCounts.medium > 0 && <span className="text-[10px] text-amber-400">⬤ {priorityCounts.medium} Medium</span>}
            {priorityCounts.low > 0 && <span className="text-[10px] text-sky-400">⬤ {priorityCounts.low} Low</span>}
          </div>
        </div>

        {/* Estimated Effort */}
        <div className="glass-panel p-5 rounded-2xl">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-sky-400" />
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Est. Effort</span>
          </div>
          <div className="text-2xl font-bold text-white">{estimatedEffort.toFixed(1)}h</div>
          <div className="text-[10px] text-slate-500 mt-1">Total refactoring time</div>
        </div>

        {/* Tech Debt Reduction */}
        <div className="glass-panel p-5 rounded-2xl">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Tech Debt Red.</span>
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            -{estimatedTechnicalDebtReduction ? estimatedTechnicalDebtReduction.toFixed(1) : (estimatedEffort * 1.5).toFixed(1)}h
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Estimated debt reduction</div>
        </div>

        {/* Complexity Reduction */}
        <div className="glass-panel p-5 rounded-2xl">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 className="w-4 h-4 text-indigo-400" />
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Complexity Red.</span>
          </div>
          <div className="text-2xl font-bold text-indigo-300">
            -{estimatedComplexityReduction ? estimatedComplexityReduction.toFixed(0) : Math.min(100, findings.length * 12).toFixed(0)}%
          </div>
          <div className="text-[10px] text-slate-500 mt-1">Cyclomatic & cognitive</div>
        </div>
      </div>

      {/* Category Distribution */}
      {Object.keys(categoryCounts).length > 0 && (
        <div className="glass-panel p-5 rounded-2xl">
          <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-3">Category Distribution</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(categoryCounts)
              .sort(([, a], [, b]) => b - a)
              .map(([cat, count]) => (
                <button
                  key={cat}
                  onClick={() => { setCategoryFilter(categoryFilter === cat ? 'all' : cat as RefactoringCategory); setPage(0); }}
                  className={`px-3 py-1.5 rounded-lg text-[11px] font-medium border transition-all ${
                    categoryFilter === cat
                      ? 'bg-violet-600/20 border-violet-500/40 text-violet-300'
                      : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-slate-600'
                  }`}
                >
                  {CATEGORY_LABELS[cat] || cat} <span className="font-mono ml-1 opacity-70">{count}</span>
                </button>
              ))}
          </div>
        </div>
      )}

      {/* Findings List */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Wrench className="w-4 h-4 text-violet-400" /> Refactoring Recommendations
        </h2>

        {/* Filters row */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search suggestions…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              className="w-full pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            <select
              value={priorityFilter}
              onChange={(e) => { setPriorityFilter(e.target.value as FindingSeverity | 'all'); setPage(0); }}
              className="pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none"
            >
              {(['all', 'critical', 'high', 'medium', 'low', 'info'] as const).map((s) => (
                <option key={s} value={s}>
                  {s === 'all' ? 'All Priorities' : s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div className="relative">
            <Filter className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            <select
              value={categoryFilter}
              onChange={(e) => { setCategoryFilter(e.target.value as RefactoringCategory | 'all'); setPage(0); }}
              className="pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none"
            >
              <option value="all">All Categories</option>
              {ALL_CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABELS[c] || c}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-2">
            {(['priority', 'effort', 'confidence'] as const).map((f) => (
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

        {/* Findings */}
        <div className="space-y-2">
          {paginated.length === 0 ? (
            <div className="flex items-center gap-2 p-4 text-xs text-slate-500">
              <Info className="w-4 h-4" /> No suggestions match your filters.
            </div>
          ) : (
            paginated.map((f, i) => (
              <RefactoringRow key={`${f.file_path}-${f.refactoring_type}-${i}`} finding={f} index={page * PAGE_SIZE + i} />
            ))
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-500">
              Page {page + 1} of {totalPages} · {filtered.length} suggestions
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
    </div>
  );
};
