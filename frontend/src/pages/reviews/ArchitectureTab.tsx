import React, { useState, useMemo } from 'react';
import {
  ArchitectureFinding,
  ArchitectureCategory,
  FindingSeverity,
  DependencyAnalysisResult,
  CategoryAnalysisMetadata,
  CodeReview,
} from '../../api/reviews';
import {
  CategoryStatusCard,
  FindingSeverityCounts,
} from './CategoryStatusCard';
import {
  Search,
  Filter,
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Flame,
  FileCode2,
} from 'lucide-react';

export interface ArchitectureTabProps {
  findings: ArchitectureFinding[];
  overallHealthScore?: number | null;
  architectureScore?: number | null;
  maintainabilityScore?: number | null;
  technicalDebtScore?: number | null;
  complexityScore?: number | null;
  documentationScore?: number | null;
  modularityScore?: number | null;
  testabilityScore?: number | null;
  dependencyAnalysis?: DependencyAnalysisResult;
  reviewStatus?: CodeReview['status'];
  categoryMetadata?: CategoryAnalysisMetadata;
}

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

// ─── Metric Score Ring ─────────────────────────────────────────────────────

const ScoreRing: React.FC<{ score: number | null | undefined; label: string }> = ({ score, label }) => {
  if (score === null || score === undefined) {
    return (
      <div className="flex flex-col items-center justify-center">
        <div className="relative w-24 h-24">
          <svg className="transform -rotate-90 w-24 h-24" viewBox="0 0 100 100">
            <circle
              className="text-slate-800"
              strokeWidth="6"
              stroke="currentColor"
              fill="none"
              r={40}
              cx="50"
              cy="50"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-sm font-semibold text-slate-500">N/A</span>
          </div>
        </div>
        <span className="text-[11px] font-semibold text-slate-400 mt-2 text-center">{label}</span>
      </div>
    );
  }

  const rounded = Math.round(score);
  let colorClass = 'stroke-emerald-400 text-emerald-400';
  if (rounded < 60) colorClass = 'stroke-rose-400 text-rose-400';
  else if (rounded < 80) colorClass = 'stroke-amber-400 text-amber-400';

  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (rounded / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative w-24 h-24">
        <svg className="transform -rotate-90 w-24 h-24" viewBox="0 0 100 100">
          <circle
            className="text-slate-800"
            strokeWidth="6"
            stroke="currentColor"
            fill="none"
            r={radius}
            cx="50"
            cy="50"
          />
          <circle
            className={`${colorClass} transition-all duration-700 ease-out`}
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            stroke="currentColor"
            fill="none"
            r={radius}
            cx="50"
            cy="50"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-xl font-bold ${colorClass.split(' ')[1]}`}>{rounded}%</span>
        </div>
      </div>
      <span className="text-[11px] font-semibold text-slate-400 mt-2 text-center">{label}</span>
    </div>
  );
};

// ─── Finding Card ────────────────────────────────────────────────────────────

const ArchitectureFindingCard: React.FC<{
  finding: ArchitectureFinding;
  index: number;
}> = ({ finding, index }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40 hover:border-slate-700/80 transition-all">
      <button
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-slate-800/40 transition-colors"
        onClick={() => setExpanded((x) => !x)}
        aria-expanded={expanded}
      >
        <span className="text-xs text-slate-500 font-mono w-5 pt-0.5 shrink-0">{index + 1}</span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            <SeverityBadge severity={finding.severity} />
            <span className="text-[10px] text-indigo-300 font-medium bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-md capitalize">
              {finding.category.replace('_', ' ')}
            </span>
            {finding.file_path && (
              <span className="text-[10px] text-slate-300 font-mono bg-slate-800 border border-slate-700 px-2 py-0.5 rounded-md truncate max-w-[280px]">
                {finding.file_path}
                {finding.line_number ? `:${finding.line_number}` : ''}
              </span>
            )}
            <span className="text-[10px] text-slate-500 ml-auto">
              Est. {finding.estimated_effort_hours}h • {Math.round(finding.confidence_score * 100)}% confidence
            </span>
          </div>
          <div className="text-sm font-medium text-slate-200">{finding.explanation}</div>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-800/80 pt-3 bg-slate-900/60 text-xs">
          {finding.root_cause && (
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-400" /> Root Cause
              </div>
              <p className="text-slate-300 leading-relaxed bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
                {finding.root_cause}
              </p>
            </div>
          )}

          {finding.business_impact && (
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1">
                <ShieldAlert className="w-3 h-3 text-rose-400" /> Business Impact
              </div>
              <p className="text-rose-300/90 leading-relaxed bg-rose-500/5 p-2.5 rounded-lg border border-rose-500/10">
                {finding.business_impact}
              </p>
            </div>
          )}

          {finding.recommendation && (
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold mb-1 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Architecture Recommendation
              </div>
              <p className="text-emerald-300/90 leading-relaxed bg-emerald-500/5 p-2.5 rounded-lg border border-emerald-500/10">
                {finding.recommendation}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ─── Main Tab Component ──────────────────────────────────────────────────────

export const ArchitectureTab: React.FC<ArchitectureTabProps> = ({
  findings = [],
  overallHealthScore = null,
  architectureScore = null,
  maintainabilityScore = null,
  technicalDebtScore = null,
  complexityScore = null,
  documentationScore = null,
  modularityScore = null,
  testabilityScore = null,
  dependencyAnalysis,
  reviewStatus = 'completed',
  categoryMetadata,
}) => {
  const [search, setSearch] = useState('');
  const [catFilter, setCatFilter] = useState<ArchitectureCategory | 'all'>('all');
  const [sevFilter, setSevFilter] = useState<FindingSeverity | 'all'>('all');
  const [sortField, setSortField] = useState<'severity' | 'effort' | 'confidence' | 'file'>('severity');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const PAGE = 10;

  const health = overallHealthScore;
  const arch = architectureScore;
  const maint = maintainabilityScore;
  const debt = technicalDebtScore;
  const comp = complexityScore;
  const doc = documentationScore;
  const mod = modularityScore;
  const test = testabilityScore;

  const layerViolations = dependencyAnalysis?.layer_violations || [];
  const hotspotFiles = dependencyAnalysis?.hotspot_files || [];

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
          f.explanation.toLowerCase().includes(q) ||
          f.category.toLowerCase().includes(q) ||
          (f.file_path || '').toLowerCase().includes(q) ||
          (f.recommendation || '').toLowerCase().includes(q)
      );
    }
    if (catFilter !== 'all') list = list.filter((f) => f.category === catFilter);
    if (sevFilter !== 'all') list = list.filter((f) => f.severity === sevFilter);

    list.sort((a, b) => {
      if (sortField === 'severity') {
        const d = (SEV_PRIORITY[b.severity] ?? 1) - (SEV_PRIORITY[a.severity] ?? 1);
        return sortDir === 'desc' ? d : -d;
      }
      if (sortField === 'effort') {
        const d = (b.estimated_effort_hours || 0) - (a.estimated_effort_hours || 0);
        return sortDir === 'desc' ? d : -d;
      }
      if (sortField === 'confidence') {
        const d = b.confidence_score - a.confidence_score;
        return sortDir === 'desc' ? d : -d;
      }
      const d = (a.file_path || '').localeCompare(b.file_path || '');
      return sortDir === 'desc' ? -d : d;
    });

    return list;
  }, [findings, search, catFilter, sevFilter, sortField, sortDir]);

  const totalPages = Math.ceil(filtered.length / PAGE);
  const paginated = filtered.slice(page * PAGE, page * PAGE + PAGE);

  const toggleSort = (f: 'severity' | 'effort' | 'confidence' | 'file') => {
    if (sortField === f) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortField(f);
      setSortDir('desc');
    }
    setPage(0);
  };

  return (
    <div className="space-y-6">
      {/* Overall Health & Metrics Dashboard */}
      <div className="glass-panel p-6 rounded-2xl">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-6">
          <Layers className="w-4 h-4 text-indigo-400" /> Architecture & Repository Health Dashboard
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
          <ScoreRing score={health} label="Overall Health" />
          <ScoreRing score={arch} label="Architecture" />
          <ScoreRing score={maint} label="Maintainability" />
          <ScoreRing score={debt} label="Tech Debt" />
          <ScoreRing score={comp} label="Complexity" />
          <ScoreRing score={doc} label="Documentation" />
          <ScoreRing score={mod} label="Modularity" />
          <ScoreRing score={test} label="Testability" />
        </div>
      </div>

      {/* Layer Violations & Hotspot Files Section */}
      {(layerViolations.length > 0 || hotspotFiles.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Layer Violations */}
          {layerViolations.length > 0 && (
            <div className="glass-panel p-5 rounded-2xl space-y-3">
              <h3 className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert className="w-4 h-4" /> Clean Architecture Layer Violations ({layerViolations.length})
              </h3>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {layerViolations.map((v, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-rose-500/5 border border-rose-500/20 rounded-xl text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between text-[11px] font-mono text-rose-300 font-semibold">
                      <span>{v.source_layer} → {v.target_layer}</span>
                    </div>
                    <p className="text-slate-300">{v.description}</p>
                    <div className="text-[10px] text-slate-400 font-mono truncate">
                      {v.source_file} imports {v.target_file}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Hotspot Files */}
          {hotspotFiles.length > 0 && (
            <div className="glass-panel p-5 rounded-2xl space-y-3">
              <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-2">
                <Flame className="w-4 h-4" /> Complexity & Tech Debt Hotspot Files ({hotspotFiles.length})
              </h3>
              <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                {hotspotFiles.map((h, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl text-xs flex items-center justify-between"
                  >
                    <div className="min-w-0 pr-2">
                      <div className="font-mono text-slate-200 truncate">{h.file_path}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        {h.issue_count} issues detected
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 text-right font-mono">
                      <div>
                        <div className="text-[9px] text-slate-500 uppercase">Comp. Score</div>
                        <div className="text-amber-300 font-bold">{h.complexity_score}</div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-500 uppercase">Debt (hrs)</div>
                        <div className="text-orange-400 font-bold">{h.technical_debt_hours}h</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Findings Section */}
      <div className="glass-panel p-6 rounded-2xl space-y-4">
        {findings.length > 0 && (
          <CategoryStatusCard
            categoryKey="architecture"
            reviewStatus={reviewStatus}
            metadata={categoryMetadata}
            findingsCount={findings.length}
            severityCounts={severityCounts}
          />
        )}

        {findings.length > 0 && (
          <>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <FileCode2 className="w-4 h-4 text-indigo-400" /> Architecture & Maintainability Findings
                  <span className="text-xs text-slate-500 font-mono">({filtered.length})</span>
                </h3>
              </div>
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Search architecture & quality findings..."
                  className="w-full pl-9 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="relative">
                <Filter className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                <select
                  value={catFilter}
                  onChange={(e) => {
                    setCatFilter(e.target.value as ArchitectureCategory | 'all');
                    setPage(0);
                  }}
                  className="pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none capitalize"
                >
                  <option value="all">All Categories</option>
                  <option value="clean_architecture">Clean Architecture</option>
                  <option value="coupling">Coupling</option>
                  <option value="cohesion">Cohesion</option>
                  <option value="solid">SOLID</option>
                  <option value="patterns">Design Patterns</option>
                  <option value="technical_debt">Tech Debt</option>
                  <option value="complexity">Complexity</option>
                  <option value="documentation">Documentation</option>
                  <option value="testability">Testability</option>
                  <option value="layer_violation">Layer Violation</option>
                  <option value="modularity">Modularity</option>
                </select>
              </div>

              <div className="relative">
                <Filter className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500 pointer-events-none" />
                <select
                  value={sevFilter}
                  onChange={(e) => {
                    setSevFilter(e.target.value as FindingSeverity | 'all');
                    setPage(0);
                  }}
                  className="pl-8 pr-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none"
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                  <option value="info">Info</option>
                </select>
              </div>

              <div className="flex gap-2">
                {(['severity', 'effort', 'confidence', 'file'] as const).map((f) => (
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
          </>
        )}

        {/* Findings List */}
        <div className="space-y-3">
          {findings.length === 0 ? (
            <CategoryStatusCard
              categoryKey="architecture"
              reviewStatus={reviewStatus}
              metadata={categoryMetadata}
              findingsCount={0}
              severityCounts={severityCounts}
            />
          ) : paginated.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 space-y-2">
              <Layers className="w-10 h-10 text-slate-600" />
              <p className="text-sm font-medium text-slate-300">
                No findings match your selected search or filter criteria.
              </p>
            </div>
          ) : (
            paginated.map((f, i) => (
              <ArchitectureFindingCard
                key={`${f.file_path || 'general'}-${i}`}
                finding={f}
                index={page * PAGE + i}
              />
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
