import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  reportsApi,
  EngineeringReport,
  ExportFormat,
  ReportComparisonResult,
  ReportContent,
} from '../../api/reports';
import {
  FileText,
  Download,
  Trash2,
  RefreshCw,
  GitCompare,
  TrendingUp,
  TrendingDown,
  Minus,
  Shield,
  Zap,
  Layers,
  Wrench,
  Code2,
  Brain,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Loader2,
  X,
  BarChart3,
  Activity,
  BookOpen,
  Target,
} from 'lucide-react';

// ── Helpers ───────────────────────────────────────────────────────────────────

const SCORE_COLOR = (score: number): string => {
  if (score >= 80) return 'text-emerald-400';
  if (score >= 60) return 'text-amber-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-rose-400';
};

const SCORE_BG = (score: number): string => {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-amber-500';
  if (score >= 40) return 'bg-orange-500';
  return 'bg-rose-500';
};

const RISK_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  critical: { color: 'text-rose-400',   bg: 'bg-rose-500/10',   border: 'border-rose-500/30' },
  high:     { color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/30' },
  medium:   { color: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/30' },
  low:      { color: 'text-emerald-400',bg: 'bg-emerald-500/10',border: 'border-emerald-500/30' },
};

const PRIORITY_STYLE: Record<string, string> = {
  critical: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
  high:     'text-orange-400 bg-orange-500/10 border-orange-500/30',
  medium:   'text-amber-400 bg-amber-500/10 border-amber-500/30',
  low:      'text-sky-400 bg-sky-500/10 border-sky-500/30',
};

const fmt = (d: string) => new Date(d).toLocaleDateString('en-US', {
  year: 'numeric', month: 'short', day: 'numeric',
});


// ── Export button ─────────────────────────────────────────────────────────────

const EXPORT_FORMATS: { fmt: ExportFormat; label: string; ext: string }[] = [
  { fmt: 'markdown', label: 'Markdown',   ext: '.md'    },
  { fmt: 'html',     label: 'HTML',       ext: '.html'  },
  { fmt: 'json',     label: 'JSON',       ext: '.json'  },
  { fmt: 'sarif',    label: 'SARIF',      ext: '.sarif' },
  { fmt: 'pdf',      label: 'PDF',        ext: '.pdf'   },
];

const ExportToolbar: React.FC<{ reportId: string; reportTitle: string }> = ({
  reportId, reportTitle,
}) => {
  const [exporting, setExporting] = useState<ExportFormat | null>(null);

  const handleExport = async (format: ExportFormat, ext: string) => {
    setExporting(format);
    try {
      const blob = await reportsApi.exportReport(reportId, format);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = `${reportTitle.replace(/\s+/g, '_')}_${reportId.slice(0, 8)}${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export failed', e);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {EXPORT_FORMATS.map(({ fmt: f, label, ext }) => (
        <button
          key={f}
          id={`export-btn-${f}`}
          onClick={() => handleExport(f, ext)}
          disabled={exporting !== null}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-indigo-600/20 hover:border-indigo-500/40 border border-slate-700 text-xs text-slate-300 hover:text-indigo-300 transition-all disabled:opacity-50"
        >
          {exporting === f ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : (
            <Download className="w-3 h-3" />
          )}
          {label}
        </button>
      ))}
    </div>
  );
};

// ── Metric score card ─────────────────────────────────────────────────────────

const MetricCard: React.FC<{
  label: string; score: number; icon: React.ReactNode; description?: string;
}> = ({ label, score, icon, description }) => (
  <div className="glass-panel p-4 rounded-xl flex flex-col gap-2">
    <div className="flex items-center gap-2">
      <span className="text-indigo-400">{icon}</span>
      <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">{label}</span>
    </div>
    <div className={`text-3xl font-black font-mono ${SCORE_COLOR(score)}`}>{score.toFixed(1)}</div>
    <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
      <div className={`h-full rounded-full ${SCORE_BG(score)}`} style={{ width: `${score}%` }} />
    </div>
    {description && <p className="text-[10px] text-slate-500">{description}</p>}
  </div>
);

// ── Report detail panel ───────────────────────────────────────────────────────

const ReportDetailPanel: React.FC<{
  report: EngineeringReport;
  onClose: () => void;
  onDelete: (id: string) => void;
}> = ({ report, onClose, onDelete }) => {
  const content: ReportContent = report.report_content || {};
  const metrics = content.metrics;
  const riskStyle = RISK_STYLE[content.risk_level || 'medium'] || RISK_STYLE.medium;
  const [activeSection, setActiveSection] = useState<string>('overview');

  const sections = [
    { id: 'overview',   label: 'Overview',       icon: <BarChart3 className="w-3.5 h-3.5" /> },
    { id: 'actions',    label: 'Action Plan',     icon: <Target className="w-3.5 h-3.5" /> },
    { id: 'security',   label: 'Security',        icon: <Shield className="w-3.5 h-3.5" /> },
    { id: 'perf',       label: 'Performance',     icon: <Zap className="w-3.5 h-3.5" /> },
    { id: 'refactor',   label: 'Refactoring',     icon: <Wrench className="w-3.5 h-3.5" /> },
    { id: 'arch',       label: 'Architecture',    icon: <Layers className="w-3.5 h-3.5" /> },
    { id: 'future',     label: 'Future',          icon: <BookOpen className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative ml-auto w-full max-w-3xl bg-slate-950 border-l border-slate-800 flex flex-col overflow-hidden animate-in slide-in-from-right duration-300">
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-slate-800 shrink-0">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-bold text-white">{report.title}</h2>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${riskStyle.color} ${riskStyle.bg} ${riskStyle.border}`}>
                {(content.risk_level || 'medium').toUpperCase()} RISK
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-mono">ID: {report.id}</p>
            <p className="text-[11px] text-slate-500">Generated: {fmt(report.created_at)}</p>
          </div>
          <button
            id="report-panel-close"
            aria-label="Close panel"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Export toolbar */}
        <div className="px-5 py-3 border-b border-slate-800 shrink-0">
          <ExportToolbar reportId={report.id} reportTitle={report.title} />
        </div>

        {/* Section nav */}
        <div className="flex gap-1 px-5 py-2 border-b border-slate-800 shrink-0 overflow-x-auto">
          {sections.map(s => (
            <button
              key={s.id}
              id={`report-section-${s.id}`}
              onClick={() => setActiveSection(s.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-all ${
                activeSection === s.id
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {s.icon}{s.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Overview */}
          {activeSection === 'overview' && (
            <>
              {content.executive_summary && (
                <div className="glass-panel p-4 rounded-xl space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Executive Summary</h3>
                  <p className="text-sm text-slate-300 leading-relaxed">{content.executive_summary}</p>
                </div>
              )}
              {metrics && (
                <div className="grid grid-cols-2 gap-3">
                  <MetricCard label="Overall Health" score={metrics.overall_health_score} icon={<Activity className="w-3.5 h-3.5" />} />
                  <MetricCard label="Risk Score"     score={metrics.risk_score}           icon={<AlertTriangle className="w-3.5 h-3.5" />} description="Higher = more risky" />
                  <MetricCard label="Security"       score={metrics.security_score}       icon={<Shield className="w-3.5 h-3.5" />} />
                  <MetricCard label="Performance"    score={metrics.performance_score}    icon={<Zap className="w-3.5 h-3.5" />} />
                  <MetricCard label="Architecture"   score={metrics.architecture_score}   icon={<Layers className="w-3.5 h-3.5" />} />
                  <MetricCard label="Maintainability" score={metrics.maintainability_score} icon={<Wrench className="w-3.5 h-3.5" />} />
                  <MetricCard label="Tech Debt"      score={metrics.technical_debt_score} icon={<Brain className="w-3.5 h-3.5" />} />
                  <MetricCard label="Documentation"  score={metrics.documentation_score}  icon={<BookOpen className="w-3.5 h-3.5" />} />
                </div>
              )}
              {/* Tech debt */}
              {(content.total_technical_debt_hours ?? 0) > 0 && (
                <div className="glass-panel p-4 rounded-xl space-y-3">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Technical Debt</h3>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-black font-mono text-orange-400">
                      {content.total_technical_debt_hours?.toFixed(1)}h
                    </span>
                    <span className="text-xs text-slate-500">estimated total</span>
                  </div>
                  {content.tech_debt_breakdown && Object.keys(content.tech_debt_breakdown).length > 0 && (
                    <div className="space-y-1.5">
                      {Object.entries(content.tech_debt_breakdown).map(([k, v]) => (
                        <div key={k} className="flex items-center gap-2">
                          <span className="text-[11px] text-slate-500 w-28 capitalize">{k.replace('_', ' ')}</span>
                          <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className="h-full rounded-full bg-orange-500"
                              style={{ width: `${Math.min((v / (content.total_technical_debt_hours || 1)) * 100, 100)}%` }}
                            />
                          </div>
                          <span className="text-[11px] font-mono text-orange-400 w-12 text-right">{v.toFixed(1)}h</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {content.tech_debt_summary && <p className="text-xs text-slate-400">{content.tech_debt_summary}</p>}
                </div>
              )}
              {/* Risk factors */}
              {(content.risk_factors?.length ?? 0) > 0 && (
                <div className="glass-panel p-4 rounded-xl space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Risk Factors</h3>
                  <ul className="space-y-1.5">
                    {content.risk_factors!.map((rf, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />{rf}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}

          {/* Priority Action Plan */}
          {activeSection === 'actions' && (
            <div className="space-y-3">
              <p className="text-xs text-slate-400">Prioritised action items derived from all analysis agents.</p>
              {(content.action_items?.length ?? 0) === 0 ? (
                <div className="flex flex-col items-center py-10 text-slate-500 gap-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                  <span className="text-sm">No critical actions identified.</span>
                </div>
              ) : (
                content.action_items!.map((item, i) => (
                  <div key={i} className="glass-panel p-4 rounded-xl space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${PRIORITY_STYLE[item.priority] || PRIORITY_STYLE.medium}`}>
                        {item.priority.toUpperCase()}
                      </span>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-400 border border-slate-700">
                        {item.category}
                      </span>
                      <span className="ml-auto text-[10px] text-slate-500 font-mono">{item.estimated_effort_hours.toFixed(1)}h</span>
                    </div>
                    <p className="text-sm font-semibold text-slate-200">{item.title}</p>
                    {item.description && <p className="text-xs text-slate-400 leading-relaxed">{item.description}</p>}
                    {item.agent_source && (
                      <span className="text-[10px] text-indigo-400 font-mono">Source: {item.agent_source}</span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* Security */}
          {activeSection === 'security' && (
            <div className="space-y-3">
              {content.security_summary && (
                <div className="glass-panel p-4 rounded-xl">
                  <p className="text-sm text-slate-300 leading-relaxed">{content.security_summary}</p>
                </div>
              )}
              <p className="text-xs text-slate-500">{content.security_findings?.length ?? 0} security findings</p>
              {(content.security_findings || []).slice(0, 12).map((f: any, i: number) => (
                <div key={i} className="glass-panel p-3 rounded-xl space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${PRIORITY_STYLE[f.severity] || PRIORITY_STYLE.medium}`}>
                      {(f.severity || 'info').toUpperCase()}
                    </span>
                    {f.file_path && <span className="text-[10px] font-mono text-indigo-300 bg-indigo-500/10 px-1.5 py-0.5 rounded">{f.file_path}</span>}
                  </div>
                  <p className="text-xs text-slate-200 font-medium">{f.issue || f.title}</p>
                  {f.explanation && <p className="text-[11px] text-slate-400">{f.explanation}</p>}
                </div>
              ))}
            </div>
          )}

          {/* Performance */}
          {activeSection === 'perf' && (
            <div className="space-y-3">
              {content.performance_summary && (
                <div className="glass-panel p-4 rounded-xl">
                  <p className="text-sm text-slate-300 leading-relaxed">{content.performance_summary}</p>
                </div>
              )}
              <p className="text-xs text-slate-500">{content.performance_findings?.length ?? 0} performance findings</p>
              {(content.performance_findings || []).slice(0, 12).map((f: any, i: number) => (
                <div key={i} className="glass-panel p-3 rounded-xl space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${PRIORITY_STYLE[f.severity] || PRIORITY_STYLE.medium}`}>
                      {(f.severity || 'info').toUpperCase()}
                    </span>
                    {f.file_path && <span className="text-[10px] font-mono text-indigo-300 bg-indigo-500/10 px-1.5 py-0.5 rounded">{f.file_path}</span>}
                  </div>
                  <p className="text-xs text-slate-200 font-medium">{f.issue}</p>
                  {f.suggested_optimization && <p className="text-[11px] text-emerald-300">{f.suggested_optimization}</p>}
                </div>
              ))}
            </div>
          )}

          {/* Refactoring */}
          {activeSection === 'refactor' && (
            <div className="space-y-3">
              {content.refactoring_summary && (
                <div className="glass-panel p-4 rounded-xl">
                  <p className="text-sm text-slate-300 leading-relaxed">{content.refactoring_summary}</p>
                </div>
              )}
              <p className="text-xs text-slate-500">{content.refactoring_findings?.length ?? 0} refactoring recommendations</p>
              {(content.refactoring_findings || []).slice(0, 12).map((f: any, i: number) => (
                <div key={i} className="glass-panel p-3 rounded-xl space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${PRIORITY_STYLE[f.priority] || PRIORITY_STYLE.medium}`}>
                      {(f.priority || 'medium').toUpperCase()}
                    </span>
                    <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">{f.category}</span>
                    {f.file_path && <span className="text-[10px] font-mono text-indigo-300">{f.file_path}</span>}
                  </div>
                  <p className="text-xs text-slate-200 font-medium">{f.refactoring_type}</p>
                  {f.explanation && <p className="text-[11px] text-slate-400">{f.explanation}</p>}
                  {f.suggested_refactoring && <p className="text-[11px] text-emerald-300">{f.suggested_refactoring}</p>}
                </div>
              ))}
            </div>
          )}

          {/* Architecture */}
          {activeSection === 'arch' && (
            <div className="space-y-3">
              {content.architecture_summary && (
                <div className="glass-panel p-4 rounded-xl">
                  <p className="text-sm text-slate-300 leading-relaxed">{content.architecture_summary}</p>
                </div>
              )}
              {/* Hotspots */}
              {(content.hotspot_files?.length ?? 0) > 0 && (
                <div className="glass-panel p-4 rounded-xl space-y-2">
                  <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Hotspot Files</h3>
                  <div className="space-y-2">
                    {content.hotspot_files!.slice(0, 8).map((h: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <span className="font-mono text-indigo-300 truncate flex-1">{h.file_path}</span>
                        <span className="text-slate-500 shrink-0">complexity: <span className="text-amber-400 font-mono">{h.complexity_score?.toFixed(0)}</span></span>
                        <span className="text-slate-500 shrink-0">debt: <span className="text-orange-400 font-mono">{h.technical_debt_hours?.toFixed(1)}h</span></span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <p className="text-xs text-slate-500">{content.architecture_findings?.length ?? 0} architecture findings</p>
              {(content.architecture_findings || []).slice(0, 12).map((f: any, i: number) => (
                <div key={i} className="glass-panel p-3 rounded-xl space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${PRIORITY_STYLE[f.severity] || PRIORITY_STYLE.medium}`}>
                      {(f.severity || 'info').toUpperCase()}
                    </span>
                    <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">{f.category}</span>
                  </div>
                  <p className="text-xs text-slate-200 font-medium">{f.explanation}</p>
                  {f.recommendation && <p className="text-[11px] text-emerald-300">{f.recommendation}</p>}
                </div>
              ))}
            </div>
          )}

          {/* Future Improvements */}
          {activeSection === 'future' && (
            <div className="space-y-3">
              {content.future_improvements_summary && (
                <div className="glass-panel p-4 rounded-xl">
                  <p className="text-sm text-slate-300 leading-relaxed">{content.future_improvements_summary}</p>
                </div>
              )}
              <div className="space-y-2">
                {(content.future_improvements || []).map((fi: string, i: number) => (
                  <div key={i} className="flex items-start gap-3 glass-panel p-3 rounded-xl">
                    <span className="w-5 h-5 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-[10px] font-bold text-indigo-400 shrink-0 mt-0.5">{i + 1}</span>
                    <p className="text-xs text-slate-300 leading-relaxed">{fi}</p>
                  </div>
                ))}
                {(content.future_improvements?.length ?? 0) === 0 && (
                  <p className="text-xs text-slate-500 py-4 text-center">No future improvements specified.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Delete footer */}
        <div className="p-4 border-t border-slate-800 shrink-0">
          <button
            id="report-delete-btn"
            onClick={() => { onDelete(report.id); onClose(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 text-xs transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" /> Delete Report
          </button>
        </div>
      </div>
    </div>
  );
};

// ── Comparison modal ──────────────────────────────────────────────────────────

const ComparisonModal: React.FC<{
  reports: EngineeringReport[];
  onClose: () => void;
}> = ({ reports, onClose }) => {
  const [idA, setIdA] = useState('');
  const [idB, setIdB] = useState('');
  const [result, setResult] = useState<ReportComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const compare = async () => {
    if (!idA || !idB || idA === idB) return;
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await reportsApi.compareReports(idA, idB);
      setResult(data);
    } catch (e: any) {
      setError(e?.message || 'Comparison failed.');
    } finally {
      setLoading(false);
    }
  };

  const deltaIcon = (v: number) =>
    v > 0 ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
    : v < 0 ? <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
    : <Minus className="w-3.5 h-3.5 text-slate-500" />;

  const deltaClass = (v: number) =>
    v > 0 ? 'text-emerald-400' : v < 0 ? 'text-rose-400' : 'text-slate-500';

  const METRIC_LABELS: Record<string, string> = {
    overall_health_score: 'Overall Health', risk_score: 'Risk',
    security_score: 'Security', performance_score: 'Performance',
    architecture_score: 'Architecture', maintainability_score: 'Maintainability',
    technical_debt_score: 'Tech Debt', complexity_score: 'Complexity',
    documentation_score: 'Documentation', testability_score: 'Testability',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-slate-950 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-5 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Compare Reports</h2>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-5 space-y-4 overflow-y-auto">
          <div className="grid grid-cols-2 gap-3">
            {[{ label: 'Report A (Baseline)', val: idA, set: setIdA },
              { label: 'Report B (Compare)', val: idB, set: setIdB }].map(({ label, val, set }) => (
              <div key={label}>
                <label className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold mb-1 block">{label}</label>
                <select
                  value={val}
                  onChange={e => set(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select report…</option>
                  {reports.map(r => (
                    <option key={r.id} value={r.id}>
                      {r.title} — {fmt(r.created_at)} ({r.overall_health_score.toFixed(0)}/100)
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <button
            id="compare-submit-btn"
            onClick={compare}
            disabled={!idA || !idB || idA === idB || loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold disabled:opacity-40 transition-all"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitCompare className="w-4 h-4" />}
            Compare
          </button>
          {error && <p className="text-xs text-rose-400">{error}</p>}
          {result && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Score Deltas</h3>
              <div className="space-y-2">
                {Object.entries(result.score_deltas).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between glass-panel p-2.5 rounded-lg">
                    <span className="text-xs text-slate-400">{METRIC_LABELS[k] || k}</span>
                    <div className="flex items-center gap-1.5">
                      {deltaIcon(v)}
                      <span className={`font-mono text-xs font-bold ${deltaClass(v)}`}>
                        {v > 0 ? '+' : ''}{v.toFixed(1)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider pt-2">Finding Count Changes</h3>
              <div className="space-y-2">
                {Object.entries(result.finding_count_deltas).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between glass-panel p-2.5 rounded-lg">
                    <span className="text-xs text-slate-400 capitalize">{k.replace('_', ' ')}</span>
                    <span className={`font-mono text-xs font-bold ${v < 0 ? 'text-emerald-400' : v > 0 ? 'text-rose-400' : 'text-slate-500'}`}>
                      {v > 0 ? '+' : ''}{v}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

export const ReportsPage: React.FC = () => {
  const navigate = useNavigate();
  const [reports, setReports] = useState<EngineeringReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedReport, setSelectedReport] = useState<EngineeringReport | null>(null);
  const [showCompare, setShowCompare] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const fetchReports = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const data = await reportsApi.listReports();
      setReports(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to load reports.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchReports(); }, [fetchReports]);

  const handleDelete = async (id: string) => {
    try {
      await reportsApi.deleteReport(id);
      setReports(rs => rs.filter(r => r.id !== id));
    } catch (e) { console.error('Delete failed', e); }
  };

  const filtered = useMemo(() => {
    let list = [...reports];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(r =>
        r.title.toLowerCase().includes(q) ||
        r.repository_id.toLowerCase().includes(q) ||
        r.id.includes(q)
      );
    }
    if (statusFilter !== 'all') list = list.filter(r => r.status === statusFilter);
    return list;
  }, [reports, search, statusFilter]);

  const avgHealth = reports.length
    ? (reports.reduce((s, r) => s + r.overall_health_score, 0) / reports.length).toFixed(1)
    : '—';

  const criticalCount = reports.filter(r => {
    const rl = r.report_content?.risk_level;
    return rl === 'critical' || rl === 'high';
  }).length;

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-indigo-400" />
            Engineering Reports
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Aggregated AI-generated engineering reports across all analysis agents
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            id="compare-reports-btn"
            onClick={() => setShowCompare(true)}
            disabled={reports.length < 2}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:border-indigo-500/40 hover:text-indigo-300 disabled:opacity-40 transition-all"
          >
            <GitCompare className="w-3.5 h-3.5" /> Compare
          </button>
          <button
            id="refresh-reports-btn"
            onClick={fetchReports}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:border-slate-600 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Reports', value: reports.length, icon: <FileText className="w-4 h-4 text-indigo-400" />, color: 'text-indigo-400' },
          { label: 'Avg Health Score', value: avgHealth, icon: <Activity className="w-4 h-4 text-emerald-400" />, color: 'text-emerald-400' },
          { label: 'High Risk Repos', value: criticalCount, icon: <AlertTriangle className="w-4 h-4 text-rose-400" />, color: 'text-rose-400' },
          { label: 'Completed', value: reports.filter(r => r.status === 'completed').length, icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />, color: 'text-emerald-400' },
        ].map(c => (
          <div key={c.label} className="glass-panel p-4 rounded-2xl space-y-1">
            <div className="flex items-center gap-1.5">{c.icon}<span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">{c.label}</span></div>
            <div className={`text-2xl font-black font-mono ${c.color}`}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search by title, repo, or ID…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 placeholder:text-slate-500"
          />
          <Code2 className="absolute left-3 top-3 w-3.5 h-3.5 text-slate-500" />
        </div>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
        >
          <option value="all">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400 gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
          Loading reports…
        </div>
      ) : error ? (
        <div className="flex flex-col items-center py-16 text-slate-400 gap-2">
          <AlertTriangle className="w-8 h-8 text-rose-400" />
          <p className="text-sm text-slate-300">{error}</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 text-slate-400 gap-3">
          <FileText className="w-12 h-12 opacity-30" />
          <p className="text-sm text-slate-300">
            {reports.length === 0 ? 'No engineering reports yet.' : 'No reports match your filters.'}
          </p>
          {reports.length === 0 && (
            <p className="text-xs text-slate-500 max-w-sm text-center">
              Run a code review from the <button onClick={() => navigate('/reviews')} className="text-indigo-400 hover:underline">Reviews</button> page and generate a report.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(report => {
            const content = report.report_content || {};
            const riskStyle = RISK_STYLE[content.risk_level || 'medium'] || RISK_STYLE.medium;
            const isCompleted = report.status === 'completed';

            return (
              <div
                key={report.id}
                className="glass-panel p-5 rounded-2xl hover:border-indigo-500/30 transition-all group cursor-pointer"
                onClick={() => isCompleted && setSelectedReport(report)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors truncate">
                        {report.title}
                      </h3>
                      {/* Status */}
                      {report.status === 'completed' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-2.5 h-2.5" /> Completed
                        </span>
                      ) : report.status === 'failed' ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                          Failed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-700/40 text-slate-400 border border-slate-700 animate-pulse">
                          <Clock className="w-2.5 h-2.5" /> {report.status}
                        </span>
                      )}
                      {/* Risk level */}
                      {content.risk_level && (
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${riskStyle.color} ${riskStyle.bg} ${riskStyle.border}`}>
                          {content.risk_level.toUpperCase()} RISK
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 font-mono">
                      Repo: {report.repository_id}
                      {report.review_id && <span> · Review: {report.review_id.slice(0, 8)}…</span>}
                    </p>
                    {/* Score row */}
                    {isCompleted && (
                      <div className="flex gap-3 flex-wrap">
                        {[
                          { label: 'Health',   score: report.overall_health_score,   icon: <Activity className="w-3 h-3" /> },
                          { label: 'Security', score: report.security_score,          icon: <Shield className="w-3 h-3" /> },
                          { label: 'Perf',     score: report.performance_score,       icon: <Zap className="w-3 h-3" /> },
                          { label: 'Arch',     score: report.architecture_score,      icon: <Layers className="w-3 h-3" /> },
                        ].map(({ label, score, icon }) => (
                          <div key={label} className="flex items-center gap-1">
                            <span className="text-slate-500">{icon}</span>
                            <span className="text-[10px] text-slate-500">{label}</span>
                            <span className={`text-[11px] font-mono font-bold ${SCORE_COLOR(score)}`}>{score.toFixed(0)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <span className="text-[10px] text-slate-500">{fmt(report.created_at)}</span>
                    {isCompleted && (
                      <div className={`text-3xl font-black font-mono ${SCORE_COLOR(report.overall_health_score)}`}>
                        {report.overall_health_score.toFixed(0)}
                        <span className="text-xs text-slate-500 font-normal">/100</span>
                      </div>
                    )}
                    <div className="flex gap-1.5">
                      {isCompleted && (
                        <button
                          id={`view-report-${report.id}`}
                          onClick={e => { e.stopPropagation(); setSelectedReport(report); }}
                          className="px-2.5 py-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-[11px] hover:bg-indigo-600/30 transition-colors"
                        >
                          View
                        </button>
                      )}
                      <button
                        id={`delete-report-${report.id}`}
                        onClick={e => { e.stopPropagation(); handleDelete(report.id); }}
                        className="p-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>

                {/* Export badges */}
                {report.export_formats.length > 0 && (
                  <div className="flex gap-1 mt-3 flex-wrap">
                    {report.export_formats.map(f => (
                      <span key={f} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">{f}</span>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Detail side panel */}
      {selectedReport && (
        <ReportDetailPanel
          report={selectedReport}
          onClose={() => setSelectedReport(null)}
          onDelete={handleDelete}
        />
      )}

      {/* Comparison modal */}
      {showCompare && (
        <ComparisonModal
          reports={reports.filter(r => r.status === 'completed')}
          onClose={() => setShowCompare(false)}
        />
      )}
    </div>
  );
};
