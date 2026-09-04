import React from 'react';
import { GitBranch, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Repository } from '../../types';
import { useRepoStore } from '../../store/useRepoStore';

interface RecentRepositoriesProps {
  repositories: Repository[];
}

export const RecentRepositories: React.FC<RecentRepositoriesProps> = ({ repositories }) => {
  const navigate = useNavigate();
  const { setActiveRepo } = useRepoStore();

  const handleOpenRepo = (repo: Repository) => {
    setActiveRepo(repo);
    navigate('/workspace');
  };

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-indigo-400" /> Recent Repositories
        </h2>
        <button
          onClick={() => navigate('/repositories')}
          className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
        >
          View all <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      <div className="space-y-3">
        {repositories.length === 0 && (
          <div className="text-sm text-slate-400 text-center py-4">No repositories found.</div>
        )}
        {repositories.slice(0, 5).map((repo) => (
          <div
            key={repo.id}
            onClick={() => handleOpenRepo(repo)}
            className="glass-card p-4 rounded-xl flex items-center justify-between cursor-pointer hover:border-indigo-500/40 group transition-colors"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-slate-100 group-hover:text-indigo-300 transition-colors">
                  {repo.name}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                  {repo.language}
                </span>
              </div>
              <div className="text-xs text-slate-400 flex items-center gap-3 font-mono">
                <span>branch: {repo.currentBranch}</span>
                <span>•</span>
                <span>{repo.chunksCount} chunks</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                {repo.indexingStatus}
              </span>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
