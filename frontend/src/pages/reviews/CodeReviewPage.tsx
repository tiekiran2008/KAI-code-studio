import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRepositoryStore } from '../../store/repositoryStore';
import { reviewsApi } from '../../api/reviews';
import {
  Code2,
  GitBranch,
  Play,
  X,
  ChevronDown,
  ShieldCheck,
  Zap,
  BookOpen,
  Settings2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
} from 'lucide-react';
import { FocusAura } from '../../components/ambient/FocusAura';

type StrictnessLevel = 'low' | 'medium' | 'high';

interface ReviewConfig {
  strictness: StrictnessLevel;
  codeQuality: boolean;
  documentation: boolean;
  architecture: boolean;
  security: boolean;
  performance: boolean;
}

const DEFAULT_CONFIG: ReviewConfig = {
  strictness: 'medium',
  codeQuality: true,
  documentation: true,
  architecture: false,
  security: true,
  performance: true,
};

const StrictnessOption: React.FC<{
  label: string;
  value: StrictnessLevel;
  color: string;
  description: string;
  selected: boolean;
  onSelect: () => void;
}> = ({ label, value: _value, color, description, selected, onSelect }) => (
  <button
    onClick={onSelect}
    className={`flex-1 p-4 rounded-xl border text-left transition-all ${
      selected
        ? `border-${color}-500/60 bg-${color}-500/10 shadow-lg`
        : 'border-slate-700 bg-slate-900/60 hover:border-slate-600'
    }`}
  >
    <div className={`text-sm font-semibold ${selected ? `text-${color}-400` : 'text-slate-300'}`}>{label}</div>
    <div className="text-xs text-slate-500 mt-1">{description}</div>
  </button>
);

const ToggleCheck: React.FC<{
  label: string;
  icon: React.ReactNode;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}> = ({ label, icon, description, checked, onChange }) => (
  <label className="flex items-center gap-4 p-4 rounded-xl border border-slate-800 bg-slate-900/40 cursor-pointer hover:border-slate-700 transition-all">
    <div className="text-slate-400">{icon}</div>
    <div className="flex-1 min-w-0">
      <div className="text-sm font-medium text-slate-200">{label}</div>
      <div className="text-xs text-slate-500 mt-0.5">{description}</div>
    </div>
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 transition-colors ${
        checked ? 'bg-indigo-600 border-indigo-600' : 'bg-slate-700 border-slate-700'
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  </label>
);

export const CodeReviewPage: React.FC = () => {
  const navigate = useNavigate();
  const { repositories, fetchRepositories } = useRepositoryStore();

  const [selectedRepo, setSelectedRepo] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('main');
  const [config, setConfig] = useState<ReviewConfig>(DEFAULT_CONFIG);
  const [status, setStatus] = useState<'idle' | 'starting' | 'in_progress' | 'done' | 'error' | 'cancelled'>('idle');
  const [progressMsg, setProgressMsg] = useState('');
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [currentStage, setCurrentStage] = useState<string>('queued');
  const [reviewId, setReviewId] = useState('');
  const [error, setError] = useState('');
  const [cancelling, setCancelling] = useState(false);

  // Polling reference
  const pollIntervalRef = React.useRef<any>(null);

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  const startPolling = (targetReviewId: string) => {
    stopPolling();

    const checkStatus = async () => {
      try {
        const review = await reviewsApi.getReview(targetReviewId);
        if (review.progress_percent !== undefined) {
          setProgressPercent(review.progress_percent);
        }
        if (review.current_stage) {
          setCurrentStage(review.current_stage);
        }
        if (review.progress_message) {
          setProgressMsg(review.progress_message);
        }

        if (review.status === 'completed') {
          stopPolling();
          setProgressPercent(100);
          setCurrentStage('completed');
          setStatus('done');
          setProgressMsg('Review complete! Redirecting to results…');
          setTimeout(() => navigate(`/reviews/${targetReviewId}`), 1200);
        } else if (review.status === 'failed') {
          stopPolling();
          setStatus('error');
          setError(review.progress_message || 'The review agent encountered an error. Please try again.');
        } else if (review.status === 'cancelled') {
          stopPolling();
          setStatus('cancelled');
          setProgressMsg(review.progress_message || 'Review cancelled by user');
        }
      } catch {
        // If 404 or network error, ignore transient failure while polling
      }
    };

    // Run initial check immediately, then poll every 2s
    checkStatus();
    pollIntervalRef.current = setInterval(checkStatus, 2000);
  };

  useEffect(() => {
    fetchRepositories();

    // Check for any currently active in-progress reviews on mount (refresh restoration)
    const restoreActiveReview = async () => {
      try {
        const activeList = await reviewsApi.listReviews({ status: 'in_progress', limit: 1 });
        if (activeList && activeList.length > 0) {
          const active = activeList[0];
          setReviewId(active.id);
          setSelectedRepo(active.repository_id);
          setStatus('in_progress');
          setProgressPercent(active.progress_percent || 10);
          setCurrentStage(active.current_stage || 'preparing');
          setProgressMsg(active.progress_message || 'Analyzing codebase…');
          startPolling(active.id);
        }
      } catch {
        // ignore restore errors
      }
    };
    restoreActiveReview();

    return () => {
      stopPolling();
    };
  }, [fetchRepositories]);

  const currentRepo = repositories.find((r) => r.id === selectedRepo);
  const branches = currentRepo?.branches?.length
    ? currentRepo.branches
    : [currentRepo?.default_branch || currentRepo?.defaultBranch || 'main'];

  const handleRepoChange = (id: string) => {
    setSelectedRepo(id);
    const repo = repositories.find((r) => r.id === id);
    setSelectedBranch(repo?.current_branch || repo?.currentBranch || repo?.default_branch || repo?.defaultBranch || 'main');
  };

  const handleStart = async () => {
    if (!selectedRepo) return;
    setStatus('starting');
    setError('');
    setProgressPercent(10);
    setCurrentStage('preparing');
    setProgressMsg('Initializing review pipeline…');

    try {
      const resp = await reviewsApi.startReview({ repository_id: selectedRepo, config });
      setReviewId(resp.review_id);
      setStatus('in_progress');
      startPolling(resp.review_id);
    } catch (e: any) {
      setStatus('error');
      setError(e?.message || 'Failed to start review. Please check your connection.');
    }
  };

  const handleCancel = async () => {
    if (!reviewId || cancelling) return;
    setCancelling(true);
    try {
      await reviewsApi.cancelReview(reviewId);
      stopPolling();
      setStatus('cancelled');
      setCurrentStage('cancelled');
      setProgressMsg('Review cancelled by user');
    } catch {
      stopPolling();
      setStatus('cancelled');
      setCurrentStage('cancelled');
      setProgressMsg('Review cancelled by user');
    } finally {
      setCancelling(false);
    }
  };

  const handleReset = () => {
    stopPolling();
    setStatus('idle');
    setProgressMsg('');
    setProgressPercent(0);
    setCurrentStage('queued');
    setReviewId('');
    setError('');
  };

  const isRunning = status === 'starting' || status === 'in_progress';


  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Code2 className="w-5 h-5 text-indigo-400" /> AI Code Review
          </h1>
          <p className="text-xs text-slate-400">
            Multi-agent analysis covering code quality, security, performance, and architecture.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/reviews/history')}
            className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-all flex items-center gap-2"
          >
            <Clock className="w-3.5 h-3.5 text-indigo-400" /> Review History
          </button>
          <div className="px-3 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-mono flex items-center gap-2">
            <Zap className="w-4 h-4 text-indigo-400 animate-pulse" /> LangGraph Multi-Agent
          </div>
        </div>
      </div>

      {/* Repository Selector */}
      <FocusAura area="review" className="glass-card p-5 rounded-2xl space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-indigo-400" /> Repository &amp; Branch
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400">Repository</label>
            <div className="relative">
              <select
                id="repo-selector"
                value={selectedRepo}
                onChange={(e) => handleRepoChange(e.target.value)}
                disabled={isRunning}
                className="w-full px-3 py-2.5 pr-8 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none disabled:opacity-50"
              >
                <option value="">— Select a repository —</option>
                {repositories.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-3 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400">Branch</label>
            <div className="relative">
              <select
                id="branch-selector"
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value)}
                disabled={isRunning || !selectedRepo}
                className="w-full px-3 py-2.5 pr-8 rounded-xl bg-slate-900 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 appearance-none disabled:opacity-50"
              >
                {branches.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2.5 top-3 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
            </div>
          </div>
        </div>
      </FocusAura>

      {/* Review Configuration */}
      <FocusAura area="review" className="glass-card p-5 rounded-2xl space-y-5">
        <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Settings2 className="w-4 h-4 text-indigo-400" /> Review Configuration
        </h2>

        {/* Strictness */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Strictness Level</label>
          <div className="flex gap-3">
            <StrictnessOption
              label="Low"
              value="low"
              color="emerald"
              description="Surface-level issues only"
              selected={config.strictness === 'low'}
              onSelect={() => setConfig((c) => ({ ...c, strictness: 'low' }))}
            />
            <StrictnessOption
              label="Medium"
              value="medium"
              color="amber"
              description="Balanced depth & speed"
              selected={config.strictness === 'medium'}
              onSelect={() => setConfig((c) => ({ ...c, strictness: 'medium' }))}
            />
            <StrictnessOption
              label="High"
              value="high"
              color="rose"
              description="Deep thorough analysis"
              selected={config.strictness === 'high'}
              onSelect={() => setConfig((c) => ({ ...c, strictness: 'high' }))}
            />
          </div>
        </div>

        {/* Checks */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">Analysis Checks</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <ToggleCheck
              label="Code Quality"
              icon={<Code2 className="w-4 h-4" />}
              description="Style, complexity, maintainability"
              checked={config.codeQuality}
              onChange={(v) => setConfig((c) => ({ ...c, codeQuality: v }))}
            />
            <ToggleCheck
              label="Security"
              icon={<ShieldCheck className="w-4 h-4" />}
              description="OWASP, CVEs, secrets detection"
              checked={config.security}
              onChange={(v) => setConfig((c) => ({ ...c, security: v }))}
            />
            <ToggleCheck
              label="Performance"
              icon={<Zap className="w-4 h-4" />}
              description="Bottlenecks, Big-O, N+1 queries"
              checked={config.performance}
              onChange={(v) => setConfig((c) => ({ ...c, performance: v }))}
            />
            <ToggleCheck
              label="Documentation"
              icon={<BookOpen className="w-4 h-4" />}
              description="Docstrings, comments coverage"
              checked={config.documentation}
              onChange={(v) => setConfig((c) => ({ ...c, documentation: v }))}
            />
            <ToggleCheck
              label="Architecture"
              icon={<Settings2 className="w-4 h-4" />}
              description="Patterns, coupling, cohesion"
              checked={config.architecture}
              onChange={(v) => setConfig((c) => ({ ...c, architecture: v }))}
            />
          </div>
        </div>
      </FocusAura>

      {/* Progress / Status */}
      {/* Progress / Status Card */}
      {status !== 'idle' && (
        <FocusAura
          area="review"
          className={`glass-card p-5 rounded-2xl space-y-3 border ${
            status === 'error'
              ? 'border-rose-500/30 bg-rose-500/5'
              : status === 'done'
              ? 'border-emerald-500/30 bg-emerald-500/5'
              : status === 'cancelled'
              ? 'border-amber-500/30 bg-amber-500/5'
              : 'border-indigo-500/20 bg-indigo-500/5'
          }`}
        >
          <div className="flex items-center gap-4">
            {status === 'error' ? (
              <AlertCircle className="w-6 h-6 text-rose-400 shrink-0" />
            ) : status === 'done' ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
            ) : status === 'cancelled' ? (
              <X className="w-6 h-6 text-amber-400 shrink-0" />
            ) : (
              <Loader2 className="w-6 h-6 text-indigo-400 shrink-0 animate-spin" />
            )}

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span
                  className={`text-sm font-medium ${
                    status === 'error'
                      ? 'text-rose-300'
                      : status === 'done'
                      ? 'text-emerald-300'
                      : status === 'cancelled'
                      ? 'text-amber-300'
                      : 'text-slate-200'
                  }`}
                >
                  {status === 'error'
                    ? 'Review Failed'
                    : status === 'done'
                    ? 'Review Complete'
                    : status === 'cancelled'
                    ? 'Review Cancelled'
                    : 'Review In Progress'}
                </span>
                <span className="text-xs font-mono font-bold text-indigo-400">
                  {progressPercent}%
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-0.5 truncate">{error || progressMsg}</div>
              {reviewId && (
                <div className="text-[10px] text-slate-500 font-mono mt-1">
                  Stage: <strong className="text-slate-400">{currentStage}</strong> | ID: {reviewId.slice(0, 8)}
                </div>
              )}
            </div>

            {isRunning && (
              <button
                id="cancel-review-btn"
                onClick={handleCancel}
                disabled={cancelling}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 disabled:opacity-50 text-xs text-rose-300 border border-rose-500/30 transition-all font-semibold"
              >
                <X className="w-3.5 h-3.5" /> {cancelling ? 'Cancelling…' : 'Cancel Review'}
              </button>
            )}

            {status === 'cancelled' && (
              <button
                onClick={handleReset}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 border border-slate-700 transition-all font-semibold"
              >
                Reset Form
              </button>
            )}
          </div>

          {/* Progress track */}
          <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden w-full">
            <div
              className={`h-full transition-all duration-500 ${
                status === 'error'
                  ? 'bg-rose-500'
                  : status === 'done'
                  ? 'bg-emerald-500'
                  : 'bg-gradient-to-r from-indigo-500 via-purple-500 to-indigo-400'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
            />
          </div>
        </FocusAura>
      )}


      {/* Start Button */}
      <div className="flex justify-end gap-3">
        {status === 'error' && (
          <button
            onClick={() => navigate('/reviews/history')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 border border-slate-700 transition-all"
          >
            <Clock className="w-4 h-4" /> View History
          </button>
        )}
        <button
          id="start-review-btn"
          onClick={handleStart}
          disabled={!selectedRepo || isRunning}
          className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-sm font-semibold text-white transition-all shadow-lg shadow-indigo-600/20"
        >
          {isRunning ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" /> Analyzing…
            </>
          ) : (
            <>
              <Play className="w-4 h-4" /> Start Review
            </>
          )}
        </button>
      </div>
    </div>
  );
};
