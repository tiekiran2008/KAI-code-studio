import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Code2, GitBranch } from 'lucide-react';
import { useDashboardData } from '../hooks/useDashboardData';
import { OverviewCards } from '../components/dashboard/OverviewCards';
import { RecentRepositories } from '../components/dashboard/RecentRepositories';
import { RecentConversations } from '../components/dashboard/RecentConversations';
import { RecentReviews } from '../components/dashboard/RecentReviews';
import { QuickActions } from '../components/dashboard/QuickActions';
import { RecentActivityTimeline } from '../components/dashboard/RecentActivityTimeline';
import { LoadingScreen } from '../components/common/LoadingScreen';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { repositories, sessions, analytics, memories, reviews, isLoadingReviews, isLoading } = useDashboardData();

  if (isLoading) {
    return <LoadingScreen isLoading={true} message="Loading dashboard data..." fullScreen={false} />;
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl glass-panel p-8 border border-indigo-500/20 shadow-glow">
        <div className="absolute -right-10 -bottom-10 w-80 h-80 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
              <Sparkles className="w-3.5 h-3.5" /> Autonomous Multi-Agent AI Software Engineering Platform
            </div>
            <h1 className="text-3xl font-bold text-white tracking-tight">
              Welcome back, Lead Architect
            </h1>
            <p className="text-slate-400 text-sm leading-relaxed">
              Your autonomous software engineering platform is operating normally. All specialized LangGraph agents and developer environment tools are ready for analysis, bug detection, and reasoning.
            </p>
          </div>

          <div className="flex flex-wrap gap-3 shrink-0">
            <button
              onClick={() => navigate('/workspace')}
              className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium text-sm shadow-glow flex items-center gap-2 transition-all"
            >
              <Code2 className="w-4 h-4" /> Open AI Workspace
            </button>
            <button
              onClick={() => navigate('/repositories')}
              className="px-4 py-2.5 rounded-xl glass-button text-slate-200 text-sm font-medium flex items-center gap-2"
            >
              <GitBranch className="w-4 h-4 text-indigo-400" /> Import Repo
            </button>
          </div>
        </div>
      </div>

      <OverviewCards repoCount={repositories.length} analytics={analytics} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentRepositories repositories={repositories} />
        <RecentReviews reviews={reviews} repositories={repositories} isLoading={isLoadingReviews} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentConversations sessions={sessions} />
        <RecentActivityTimeline memories={memories} />
      </div>

      <div className="space-y-6">
        <QuickActions />
      </div>
    </div>
  );
};
