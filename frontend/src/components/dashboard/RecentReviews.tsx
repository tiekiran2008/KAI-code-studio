import React from 'react';
import { FileSearch, ArrowRight, CheckCircle2, Clock, Loader2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { CodeReview } from '../../api/reviews';
import { Repository } from '../../types';

interface RecentReviewsProps {
  reviews: CodeReview[];
  repositories: Repository[];
  isLoading?: boolean;
}

export const RecentReviews: React.FC<RecentReviewsProps> = ({
  reviews,
  repositories,
  isLoading = false,
}) => {
  const navigate = useNavigate();

  const getRepoName = (repoId: string) => {
    const repo = repositories.find((r) => r.id === repoId);
    return repo ? `${repo.owner || ''}/${repo.name}` : repoId.slice(0, 12);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const renderStatus = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[11px] font-medium">
            <CheckCircle2 className="w-3 h-3" /> Completed
          </span>
        );
      case 'in_progress':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[11px] font-medium animate-pulse">
            <Loader2 className="w-3 h-3 animate-spin" /> In Progress
          </span>
        );
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-medium">
            <Clock className="w-3 h-3" /> Pending
          </span>
        );
      case 'cancelled':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 text-[11px] font-medium">
            <AlertTriangle className="w-3 h-3" /> Cancelled
          </span>
        );
      case 'failed':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[11px] font-medium">
            <AlertTriangle className="w-3 h-3" /> Failed
          </span>
        );
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4" data-testid="recent-reviews-card">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <FileSearch className="w-4 h-4 text-indigo-400" /> Recent Code Reviews
        </h2>
        <button
          onClick={() => navigate('/reviews/history')}
          className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
          aria-label="View all code reviews"
        >
          View all <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      <div className="space-y-3">
        {isLoading && (
          <div className="text-xs text-slate-400 text-center py-6 flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
            Loading recent reviews...
          </div>
        )}

        {!isLoading && reviews.length === 0 && (
          <div className="text-center py-6 space-y-2">
            <p className="text-xs text-slate-400">No code reviews yet.</p>
            <button
              onClick={() => navigate('/reviews')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium inline-flex items-center gap-1"
            >
              Start a review <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        )}

        {!isLoading &&
          reviews.slice(0, 4).map((review) => {
            const findingsCount = Array.isArray(review.findings)
              ? review.findings.length
              : ((review as any).findings_json as any[])?.length || 0;

            return (
              <div
                key={review.id}
                onClick={() => navigate(`/reviews/${review.id}`)}
                className="glass-card p-3.5 rounded-xl flex items-center justify-between cursor-pointer hover:border-indigo-500/40 group transition-all"
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    navigate(`/reviews/${review.id}`);
                  }
                }}
                aria-label={`View review for ${getRepoName(review.repository_id)}`}
              >
                <div className="space-y-1 min-w-0 flex-1 pr-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-xs text-slate-100 group-hover:text-indigo-300 transition-colors truncate max-w-[200px] sm:max-w-xs">
                      {getRepoName(review.repository_id)}
                    </span>
                    {renderStatus(review.status)}
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-3 font-mono">
                    <span>{formatDate(review.created_at)}</span>
                    <span>•</span>
                    <span>
                      {findingsCount} {findingsCount === 1 ? 'issue' : 'issues'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  {review.overall_health_score !== undefined && review.overall_health_score > 0 && (
                    <div className="hidden sm:flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-lg border border-emerald-500/20">
                      <ShieldCheck className="w-3 h-3" />
                      {review.overall_health_score.toFixed(0)}
                    </div>
                  )}
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
};
