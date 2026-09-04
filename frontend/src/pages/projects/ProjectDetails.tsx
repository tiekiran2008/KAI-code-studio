import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProjectStore } from '../../store/projectStore';
import { useRepositoryStore } from '../../store/repositoryStore';
import { FolderGit2, ArrowLeft, Plus, GitBranch, Trash2 } from 'lucide-react';

export const ProjectDetails: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { activeProject, dashboard, fetchProject, fetchDashboard, linkRepository, unlinkRepository } = useProjectStore();
  const { repositories, fetchRepositories } = useRepositoryStore();

  const [selectedRepoToLink, setSelectedRepoToLink] = useState('');
  const [isLinking, setIsLinking] = useState(false);

  useEffect(() => {
    if (projectId) {
      fetchProject(projectId);
      fetchDashboard(projectId);
      fetchRepositories();
    }
  }, [projectId, fetchProject, fetchDashboard, fetchRepositories]);

  const handleLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !selectedRepoToLink) return;
    setIsLinking(true);
    try {
      await linkRepository(projectId, selectedRepoToLink);
      await fetchDashboard(projectId);
      setSelectedRepoToLink('');
    } finally {
      setIsLinking(false);
    }
  };

  const handleUnlink = async (repoId: string) => {
    if (!projectId) return;
    await unlinkRepository(projectId, repoId);
    await fetchDashboard(projectId);
  };

  if (!activeProject) {
    return <div className="py-24 text-center text-xs text-slate-400">Loading project details...</div>;
  }

  const linkedRepoIds = new Set(activeProject.repositories.map((r) => r.id));
  const availableReposToLink = repositories.filter((r) => !linkedRepoIds.has(r.id));

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/projects')}
          className="flex items-center gap-2 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Projects
        </button>
      </div>

      {/* Main Info */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-950/80 border border-indigo-500/30 flex items-center justify-center">
              <FolderGit2 className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">{activeProject.name}</h1>
              <p className="text-xs text-slate-400 mt-0.5">{activeProject.description || 'No description provided.'}</p>
            </div>
          </div>
        </div>

        {/* Dashboard Metrics */}
        {dashboard && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
              <p className="text-[11px] text-slate-400 font-medium">Total Linked Repos</p>
              <p className="text-xl font-bold text-white mt-1">{dashboard.total_repositories}</p>
            </div>
            <div className="bg-slate-900/80 p-4 rounded-xl border border-emerald-900/30">
              <p className="text-[11px] text-emerald-400 font-medium">Indexed Repos</p>
              <p className="text-xl font-bold text-emerald-400 mt-1">{dashboard.indexed_repositories}</p>
            </div>
            <div className="bg-slate-900/80 p-4 rounded-xl border border-indigo-900/30">
              <p className="text-[11px] text-indigo-400 font-medium">Total Vector Chunks</p>
              <p className="text-xl font-bold text-indigo-300 mt-1">{dashboard.total_chunks.toLocaleString()}</p>
            </div>
            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800">
              <p className="text-[11px] text-slate-400 font-medium">Detected Languages</p>
              <p className="text-xs font-mono font-semibold text-slate-200 mt-2 truncate">
                {dashboard.languages.join(', ') || 'None'}
              </p>
            </div>
          </div>
        )}

        {/* Link Repository Tool */}
        <form onSubmit={handleLink} className="flex items-center gap-3 bg-slate-900/80 p-4 rounded-xl border border-slate-800">
          <div className="flex-1">
            <label className="text-xs font-medium text-slate-300 block mb-1">Link Repository to this Project</label>
            <select
              value={selectedRepoToLink}
              onChange={(e) => setSelectedRepoToLink(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:border-indigo-500"
            >
              <option value="">Select a repository to link...</option>
              {availableReposToLink.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.provider || 'github'})
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={!selectedRepoToLink || isLinking}
            className="self-end px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 shadow-glow disabled:opacity-50"
          >
            <Plus className="w-4 h-4" /> Link Repo
          </button>
        </form>

        {/* Linked Repositories Table */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-indigo-400" /> Linked Repositories ({activeProject.repositories.length})
          </h3>
          <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40">
            {activeProject.repositories.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-500">No repositories linked to this project yet.</div>
            ) : (
              activeProject.repositories.map((repo) => (
                <div key={repo.id} className="p-4 flex items-center justify-between hover:bg-slate-800/40 transition-colors">
                  <div className="flex items-center gap-3">
                    <GitBranch className="w-4 h-4 text-indigo-400 shrink-0" />
                    <div>
                      <p
                        onClick={() => navigate(`/repositories/${repo.id}`)}
                        className="text-xs font-bold text-white hover:text-indigo-400 cursor-pointer transition-colors"
                      >
                        {repo.name}
                      </p>
                      <p className="text-[11px] text-slate-500 font-mono">{repo.url}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <span className="text-xs font-mono text-slate-400">{(repo.chunks_count || repo.chunksCount || 0)} chunks</span>
                    <button
                      onClick={() => handleUnlink(repo.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10"
                      title="Unlink Repository"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
