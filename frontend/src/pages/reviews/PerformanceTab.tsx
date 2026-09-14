import React, { useMemo, useState } from 'react';
import {
  PerformanceFinding,
  PerformanceRecommendation,
  FindingSeverity,
  CategoryAnalysisMetadata,
  CodeReview,
} from '../../api/reviews';
import {
  CategoryStatusCard,
  FindingSeverityCounts,
} from './CategoryStatusCard';
import {
  Zap,
  Cpu,
  MemoryStick,
  Timer,
  ChevronDown,
  ChevronUp,
  Search,
  Filter,
  ArrowUpDown,
  TrendingDown,
  Lightbulb,
  AlertCircle,
  CheckCircle2,
  Info,
} from 'lucide-react';

// ─── Severity helpers ───────────────────────────────────────────────────────

const SEVERITY_CONFIG: Record<
  FindingSeverity,
  { label: string; color: string; bg: string; border: string; priority: number }
> = {
  critical: {
    label: 'Critical',
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    priority: 5,
  },
  high: {
    label: 'High',
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    priority: 4,
  },
  medium: {
    label: 'Medium',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    priority: 3,
  },
  low: {
    label: 'Low',
    color: 'text-sky-400',
    bg: 'bg-sky-500/10',
    border: 'border-sky-500/30',
    priority: 2,
  },
  info: {
    label: 'Info',
    color: 'text-slate-400',
    bg: 'bg-slate-700/40',
    border: 'border-slate-700',
    priority: 1,
  },
};

const SeverityBadge: React.FC<{ severity: FindingSeverity }> = ({ severity }) => {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${cfg.color} ${cfg.bg} ${cfg.border}`}
    >
      {cfg.label}
    </span>
  );
};

// ─── Score ring ─────────────────────────────────────────────────────────────

const ScoreRing: React.FC<{ score: number | null; size?: number }> = ({ score, size = 96 }) => {
  const pct = score !== null ? Math.min(100, Math.max(0, score)) : 0;
  const r = 36;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <svg width={size} height={size} viewBox="0 0 96 96" className="rotate-[-90deg]">
      <circle cx={48} cy={48} r={r} fill="none" stroke="#1e293b" strokeWidth={8} />
      <circle
        cx={48}
        cy={48}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={8}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.8s ease' }}
      />
      <text
        x={48}
        y={52}
        textAnchor="middle"
        fill="white"
        fontSize={score !== null ? 18 : 12}
        fontWeight={700}
        className="rotate-90"
        style={{ transform: 'rotate(90deg)', transformOrigin: '48px 48px' }}
      >
        {score !== null ? Math.round(score) : 'N/A'}
      </text>
    </svg>
  );
};

// ─── Metric card ────────────────────────────────────────────────────────────

const MetricCard: React.FC<{
  label: string;
  value: number;
  unit: string;
  icon: React.ReactNode;
  colorClass: string;
}> = ({ label, value, unit, icon, colorClass }) => (
  <div className="glass-card p-4 rounded-xl flex items-center gap-4">
    <div className={`p-2.5 rounded-xl ${colorClass} bg-opacity-10`}>{icon}</div>
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="text-2xl font-bold text-white font-mono">
        {value.toFixed(1)}
        <span className="text-sm font-normal text-slate-400 ml-1">{unit}</span>
      </div>
    </div>
  </div>
);

// ─── Bar chart by severity ───────────────────────────────────────────────────

const SeverityBarChart: React.FC<{ findings: PerformanceFinding[] }> = ({ findings }) => {
  const counts = useMemo(() => {
    const c: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    findings.forEach((f) => {
      if (c[f.severity] !== undefined) c[f.severity]++;
    });
    return c;
  }, [findings]);

  const max = Math.max(1, ...Object.values(counts));
  const COLORS: Record<string, string> = {
    critical: 'bg-rose-500',
    high: 'bg-orange-500',
    medium: 'bg-amber-500',
    low: 'bg-sky-500',
    info: 'bg-slate-500',
  };

  return (
    <div className="space-y-2">
      {Object.entries(counts).map(([sev, count]) => (
        <div key={sev} className="flex items-center gap-3">
          <span className="w-14 text-[11px] text-slate-400 capitalize">{sev}</span>
          <div className="flex-1 h-3 bg-slate-900 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ${COLORS[sev]}`}
              style={{ width: `${(count / max) * 100}%` }}
            />
          </div>
          <span className="w-6 text-[11px] text-slate-300 font-mono text-right">{count}</span>
        </div>
      ))}
    </div>
  );
};

// ─── Finding row ─────────────────────────────────────────────────────────────

const FindingRow: React.FC<{ finding: PerformanceFinding; index: number }> = ({ finding, index }) => {
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
            <SeverityBadge severity={finding.severity} />
            {finding.file_path && (
              <span className="text-[10px] text-indigo-300 font-mono bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-md">
                {finding.file_path}
                {finding.line_number ? `:${finding.line_number}` : ''}
              </span>
            )}
            {finding.confidence_score !== undefined && (
              <span className="text-[10px] text-slate-500 ml-auto">
                {Math.round(finding.confidence_score * 100)}% confidence
              </span>
            )}
          </div>
          <div className="text-sm font-medium text-slate-200 truncate">{finding.issue}</div>
          {finding.estimated_impact && (
            <div className="text-xs text-slate-500 mt-0.5 truncate">{finding.estimated_impact}</div>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-800/60 pt-3 bg-slate-900/30">
          {finding.root_cause && (
            <div>
              <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1">Root Cause</div>
              <p className="text-xs text-slate-300 leading-relaxed">{finding.root_cause}</p>
            </div>
          )}
          {finding.suggested_optimization && (
            <div>
              <div className="text-[11px] text-slate-500 uppercase tracking-wider font-semibold mb-1">
                Suggested Optimization
              </div>
              <p className="text-xs text-emerald-300 leading-relaxed">{finding.suggested_optimization}</p>
            </div>
          )}
          {finding.expected_performance_gain && (
            <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
              <TrendingDown className="w-3.5 h-3.5" />
              Expected gain: {finding.expected_performance_gain}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ─── Recommendations panel ──────────────────────────────────────────────────

const RecommendationsPanel: React.FC<{ recommendations: PerformanceRecommendation[] }> = ({
  recommendations,
}) => {
  if (!recommendations.length) return null;

  return (
    <div className="glass-card p-5 rounded-2xl space-y-4">
      <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
        <Lightbulb className="w-4 h-4 text-amber-400" /> Optimization Recommendations
      </h3>
      <div className="space-y-3">
        {recommendations.map((rec, i) => (
          <div key={i} className="flex items-start gap-3 p-3 bg-slate-900/60 rounded-xl border border-slate-800">
            <div className="w-6 h-6 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-[10px] font-bold text-amber-400">{i + 1}</span>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-200">{rec.title}</div>
              {rec.description && (
                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{rec.description}</p>
              )}
              {rec.impact_estimate && (
                <span className="inline-flex items-center gap-1 mt-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-[10px] text-emerald-300">
                  <TrendingDown className="w-3 h-3" /> {rec.impact_estimate}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── Main PerformanceTab ─────────────────────────────────────────────────────

interface PerformanceTabProps {
  findings: PerformanceFinding[];
  recommendations: PerformanceRecommendation[];
  performanceScore: number | null;
  estimatedCpuSavings: number;
  estimatedMemorySavings: number;
  estimatedLatencyImprovement: number;
  reviewStatus?: CodeReview['status'];
  categoryMetadata?: CategoryAnalysisMetadata;
}

type SortField = 'severity' | 'confidence' | 'file';
type SortDir = 'asc' | 'desc';

const PAGE_SIZE = 10;

export const PerformanceTab: React.FC<PerformanceTabProps> = ({
  findings,
  recommendations,
  performanceScore,
  estimatedCpuSavings,
  estimatedMemorySavings,
  estimatedLatencyImprovement,
  reviewStatus = 'completed',
  categoryMetadata,
}) => {
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState<FindingSeverity | 'all'>('all');
  const [sortField, setSortField] = useState<SortField>('severity');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(0);

  const scoreLabel =
    performanceScore === null
      ? 'N/A'
      : performanceScore >= 70
      ? 'Good'
      : performanceScore >= 40
      ? 'Fair'
      : 'Poor';

  const scoreColor =
    performanceScore === null
      ? 'text-slate-400'
      : performanceScore >= 70
      ? 'text-emerald-400'
      : performanceScore >= 40
      ? 'text-amber-400'
      : 'text-rose-400';

  const severityCounts = useMemo(() => {
    const counts: FindingSeverityCounts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    findings.forEach((f) => {
      if (f.severity in counts) counts[f.severity as keyof FindingSeverityCounts]++;
    });
    return counts;
  }, [findings]);

  const filtered = useMemo(() => {
    let list = [...findings];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(
        (f) =>
          f.issue.toLowerCase().includes(q) ||
          (f.file_path || '').toLowerCase().includes(q) ||
          (f.root_cause || '').toLowerCase().includes(q)
      );
    }
    if (severityFilter !== 'all') {
      list = list.filter((f) => f.severity === severityFilter);
    }
    list.sort((a, b) => {
      let av = 0;
      let bv = 0;
      if (sortField === 'severity') {
        av = SEVERITY_CONFIG[a.severity]?.priority ?? 1;
        bv = SEVERITY_CONFIG[b.severity]?.priority ?? 1;
      } else if (sortField === 'confidence') {
        av = a.confidence_score ?? 0;
        bv = b.confidence_score ?? 0;
      } else if (sortField === 'file') {
        return sortDir === 'asc'
          ? (a.file_path || '').localeCompare(b.file_path || '')
          : (b.file_path || '').localeCompare(a.file_path || '');
      }
      return sortDir === 'asc' ? av - bv : bv - av;
    });
    return list;
  }, [findings, search, severityFilter, sortField, sortDir]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortField(field);
      setSortDir('desc');
    }
    setPage(0);
  };

  const SEVERITIES: Array<FindingSeverity | 'all'> = ['all', 'critical', 'high', 'medium', 'low', 'info'];

  if (!findings.length) {
    const isEvaluated = categoryMetadata
      ? categoryMetadata.status === 'completed'
      : performanceScore !== null && performanceScore !== undefined;

    if (isEvaluated) {
      return (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="glass-card p-5 rounded-2xl flex items-center gap-5 col-span-1">
              <ScoreRing score={performanceScore} />
              <div>
                <div className="text-xs text-slate-400 mb-0.5">Performance Score</div>
                <div className={`text-xl font-bold ${scoreColor}`}>{scoreLabel}</div>
                <div className="text-xs text-slate-500">0 issues found</div>
              </div>
            </div>
            <MetricCard
              label="CPU Savings"
              value={estimatedCpuSavings}
              unit="%"
              icon={<Cpu className="w-5 h-5 text-indigo-400" />}
              colorClass="bg-indigo-500/10"
            />
            <MetricCard
              label="Memory Savings"
              value={estimatedMemorySavings}
              unit="%"
              icon={<MemoryStick className="w-5 h-5 text-violet-400" />}
              colorClass="bg-violet-500/10"
            />
            <MetricCard
              label="Latency Improvement"
              value={estimatedLatencyImprovement}
              unit="%"
              icon={<Timer className="w-5 h-5 text-emerald-400" />}
              colorClass="bg-emerald-500/10"
            />
          </div>
          <CategoryStatusCard
            categoryKey="performance"
            reviewStatus={reviewStatus}
            metadata={categoryMetadata}
            findingsCount={0}
            severityCounts={severityCounts}
          />
          {recommendations.length > 0 && <RecommendationsPanel recommendations={recommendations} />}
        </div>
      );
    }
    return (
      <div className="space-y-6">
        <CategoryStatusCard
          categoryKey="performance"
          reviewStatus={reviewStatus}
          metadata={categoryMetadata ?? { status: 'not_evaluated', findings_count: 0 }}
          findingsCount={0}
          severityCounts={severityCounts}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Category header when findings exist */}
      <CategoryStatusCard
        categoryKey="performance"
        reviewStatus={reviewStatus}
        metadata={categoryMetadata}
        findingsCount={findings.length}
        severityCounts={severityCounts}
      />

      {/* Score header row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        {/* Score Card */}
        <div className="glass-card p-5 rounded-2xl flex items-center gap-5 col-span-1">
          <ScoreRing score={performanceScore} />
          <div>
            <div className="text-xs text-slate-400 mb-0.5">Performance Score</div>
            <div className={`text-xl font-bold ${scoreColor}`}>{scoreLabel}</div>
            <div className="text-xs text-slate-500">{findings.length} issues found</div>
          </div>
        </div>

        {/* CPU */}
        <MetricCard
          label="CPU Savings"
          value={estimatedCpuSavings}
          unit="%"
          icon={<Cpu className="w-5 h-5 text-indigo-400" />}
          colorClass="bg-indigo-500/10"
        />

        {/* Memory */}
        <MetricCard
          label="Memory Savings"
          value={estimatedMemorySavings}
          unit="%"
          icon={<MemoryStick className="w-5 h-5 text-violet-400" />}
          colorClass="bg-violet-500/10"
        />

        {/* Latency */}
        <MetricCard
          label="Latency Improvement"
          value={estimatedLatencyImprovement}
          unit="%"
          icon={<Timer className="w-5 h-5 text-emerald-400" />}
          colorClass="bg-emerald-500/10"
        />
      </div>

      {/* Severity distribution chart */}
      <div className="glass-card p-5 rounded-2xl space-y-3">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-orange-400" /> Severity Distribution
        </h3>
        <SeverityBarChart findings={findings} />
      </div>

      {/* Recommendations */}
      <RecommendationsPanel recommendations={recommendations} />

      {/* Findings table */}
      <div className="glass-panel p-5 rounded-2xl space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Zap className="w-4 h-4 text-amber-400" /> Performance Findings
          <span className="ml-auto text-xs text-slate-500 font-normal">
            {filtered.length} of {findings.length}
          </span>
        </h3>

        {/* Filters + search */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
            <input
              id="perf-search"
              type="text"
              placeholder="Search findings…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              className="w-full pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="relative">
            <Filter className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
            <select
              id="severity-filter"
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value as FindingSeverity | 'all');
                setPage(0);
              }}
              className="pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s === 'all' ? 'All Severities' : s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-2">
            {(['severity', 'confidence', 'file'] as SortField[]).map((f) => (
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

        {/* Findings list */}
        <div className="space-y-2">
          {paginated.length === 0 ? (
            <div className="flex items-center gap-2 p-4 text-xs text-slate-500">
              <Info className="w-4 h-4" /> No findings match your filters.
            </div>
          ) : (
            paginated.map((f, i) => (
              <FindingRow key={`${f.file_path}-${i}`} finding={f} index={page * PAGE_SIZE + i} />
            ))
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <span className="text-xs text-slate-500">
              Page {page + 1} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                id="perf-prev-page"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1.5 rounded-lg bg-slate-800 disabled:opacity-40 text-xs text-slate-300 hover:bg-slate-700 border border-slate-700 transition-all"
              >
                ← Prev
              </button>
              <button
                id="perf-next-page"
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
