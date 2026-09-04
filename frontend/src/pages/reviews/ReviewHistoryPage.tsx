import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useReviewStore } from '../../store/reviewStore';
import { useRepositoryStore } from '../../store/repositoryStore';
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FileSearch,
  Plus,
  RefreshCw,
  Trash2,
  ExternalLink,
  ShieldCheck,
  Zap,
  Filter,
} from 'lucide-react';

export const ReviewHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const { history, isLoading, error, fetchUserReviews, deleteReview } = useReviewStore();
  const { repositories, fetchRepositories } = useRepositoryStore();

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedRepoFilter, setSelectedRepoFilter] = useState<string>('all');

  useEffect(() => {
    fetchRepositories();
    fetchUserReviews();
  }, [fetchRepositories, fetchUserReviews]);

  const handleRefresh = () => {
    fetchUserReviews({
      repository_id: selectedRepoFilter !== 'all' ? selectedRepoFilter : undefined,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    });
  };

  const handleRepoFilterChange = (repoId: string) => {
    setSelectedRepoFilter(repoId);
    fetchUserReviews({
      repository_id: repoId !== 'all' ? repoId : undefined,
      status: statusFilter !== 'all' ? statusFilter : undefined,
    });
  };

  const handleStatusFilterChange = (status: string) => {
    setStatusFilter(status);
    fetchUserReviews({
      repository_id: selectedRepoFilter !== 'all' ? selectedRepoFilter : undefined,
      status: status !== 'all' ? status : undefined,
    });
  };

  const handleDelete = async (e: React.MouseEvent, reviewId: string) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this review from history?')) {
      await deleteReview(reviewId);
    }
  };

  const formatDuration = (durationMs?: number) => {
    if (!durationMs) return 'N/A';
    if (durationMs < 1000) return `${durationMs}ms`;
    return `${(durationMs / 1000).toFixed(1)}s`;
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const getRepoName = (repoId: string) => {
    const repo = repositories.find((r) => r.id === repoId);
    return repo ? `${repo.owner}/${repo.name}` : repoId;
  };

  const renderStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" /> Completed
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-medium animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> In Progress
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-medium">
            <Clock className="w-3.5 h-3.5" /> Pending
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-xs font-medium">
            <AlertTriangle className="w-3.5 h-3.5" /> Cancelled
          </span>
        );
      case 'failed':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-xs font-medium">
            <AlertTriangle className="w-3.5 h-3.5" /> Failed
          </span>
        );
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FileSearch className="w-5 h-5 text-indigo-400" /> Code Review History
          </h1>
          <p className="text-xs text-slate-400">
            View all past multi-agent code analysis sessions, performance metrics, and security audits.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
            title="Refresh History"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => navigate('/reviews')}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-all shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-4 h-4" /> Start New Review
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-card p-4 rounded-2xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <Filter className="w-4 h-4 text-indigo-400" /> Filters:
        </div>

        <div className="flex flex-wrap items-center gap-3 flex-1 justify-end">
          {/* Repo Filter */}
          <select
            value={selectedRepoFilter}
            onChange={(e) => handleRepoFilterChange(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="all">All Repositories</option>
            {repositories.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.owner}/{repo.name}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => handleStatusFilterChange(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="in_progress">In Progress</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={handleRefresh}
            className="px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-xs font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading state */}
      {isLoading && history.length === 0 && (
        <div className="p-12 text-center text-slate-400 space-y-3">
          <Loader2 className="w-8 h-8 animate-spin mx-auto text-indigo-400" />
          <p className="text-xs">Loading code review history…</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && history.length === 0 && (
        <div
          className="glass-card p-12 text-center rounded-2xl space-y-4"
          data-testid="review-history-empty"
          role="status"
        >
          <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto text-indigo-400">
            <FileSearch className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-white">No Code Reviews Found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              No reviews yet. Start a new code review to inspect findings, automated fixes, and engineering reports.
            </p>
          </div>
          <button
            onClick={() => navigate('/reviews')}
            className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-all inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Start Review Now
          </button>
        </div>
      )}

      {/* History Items Grid */}
      {history.length > 0 && (
        <div className="space-y-3">
          {history.map((review) => {
            const findingsCount = Array.isArray(review.findings)
              ? review.findings.length
              : ((review as any).findings_json as any[])?.length || 0;

            return (
              <div
                key={review.id}
                onClick={() => navigate(`/reviews/${review.id}`)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(`/reviews/${review.id}`);
                  }
                }}
                role="button"
                tabIndex={0}
                aria-label={`View code review for ${getRepoName(review.repository_id)} from ${formatDate(review.created_at)}`}
                className="glass-card p-5 rounded-2xl border border-slate-800 hover:border-indigo-500/40 transition-all cursor-pointer group flex flex-col md:flex-row md:items-center justify-between gap-4 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <div className="space-y-2 min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    {renderStatusBadge(review.status)}
                    <span className="text-xs font-mono text-slate-500">ID: {review.id.slice(0, 8)}</span>
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors flex items-center gap-2 truncate">
                      {getRepoName(review.repository_id)}
                      <ExternalLink className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-indigo-400 shrink-0" />
                    </h3>
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-1">
                      <span>Date: {formatDate(review.created_at)}</span>
                      <span>Duration: {formatDuration(review.duration_ms)}</span>
                      <span>Findings: <strong className="text-slate-200">{findingsCount}</strong></span>
                    </div>
                  </div>
                </div>

                {/* Score Indicators & Delete Action */}
                <div className="flex items-center gap-4 border-t md:border-t-0 pt-3 md:pt-0 border-slate-800/80 justify-between md:justify-end shrink-0">
                  {review.overall_health_score !== undefined && review.overall_health_score > 0 && (
                    <div className="text-right">
                      <div className="text-xs text-slate-500">Health Score</div>
                      <div className="text-sm font-bold text-emerald-400 flex items-center gap-1 justify-end">
                        <ShieldCheck className="w-3.5 h-3.5" />
                        {review.overall_health_score.toFixed(1)}/100
                      </div>
                    </div>
                  )}

                  {review.performance_score !== undefined && review.performance_score > 0 && (
                    <div className="text-right">
                      <div className="text-xs text-slate-500 font-mono">Performance</div>
                      <div className="text-sm font-bold text-indigo-400 flex items-center gap-1 justify-end">
                        <Zap className="w-3.5 h-3.5" />
                        {review.performance_score.toFixed(0)}%
                      </div>
                    </div>
                  )}

                  <button
                    onClick={(e) => handleDelete(e, review.id)}
                    className="p-2 rounded-xl text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-all focus:outline-none focus:ring-2 focus:ring-rose-500/50"
                    title="Delete Review"
                    aria-label={`Delete review ${review.id.slice(0, 8)}`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
