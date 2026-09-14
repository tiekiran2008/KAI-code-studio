import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '../../store/projectStore';
import { FolderGit2, Plus, GitBranch, Archive, Trash2, ChevronRight } from 'lucide-react';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { useUIStore } from '../../store/useUIStore';

export const ProjectDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { projects, isLoading, fetchProjects, createProject, archiveProject, deleteProject } = useProjectStore();
  const { activeWorkspaceId } = useWorkspaceStore();

  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchProjects(activeWorkspaceId || undefined);
  }, [fetchProjects, activeWorkspaceId]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsCreating(true);
    try {
      await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        workspace_id: activeWorkspaceId || undefined,
      });
      setName('');
      setDescription('');
      setShowCreate(false);
      useUIStore.getState().addToast('Project created successfully', 'success');
    } catch (err: any) {
      useUIStore.getState().addToast(err.message || 'Failed to create project', 'error');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FolderGit2 className="w-6 h-6 text-indigo-400" />
            Projects
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Group multiple repositories together into unified engineering projects.
          </p>
        </div>

        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 shadow-glow transition-all"
        >
          <Plus className="w-4 h-4" /> Create Project
        </button>
      </div>

      {/* Create Modal / Card Inline */}
      {showCreate && (
        <form onSubmit={handleCreate} className="glass-panel p-6 rounded-2xl border border-indigo-500/30 space-y-4">
          <h3 className="text-sm font-semibold text-white">Create New Project</h3>
          <div className="space-y-3">
            <input
              type="text"
              required
              placeholder="Project Name (e.g., E-Commerce Platform, AI Pipeline)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500"
            />
            <textarea
              rows={2}
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-indigo-500 resize-none"
            />
          </div>
          <div className="flex items-center gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-glow"
            >
              Save Project
            </button>
          </div>
        </form>
      )}

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {isLoading ? (
          <div className="col-span-full py-16 text-center text-xs text-slate-400">Loading projects...</div>
        ) : projects.length === 0 ? (
          <div className="col-span-full py-16 text-center text-xs text-slate-400 glass-panel rounded-2xl">
            No projects created yet. Create a project to link repositories together!
          </div>
        ) : (
          projects.map((proj) => (
            <div
              key={proj.id}
              className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-indigo-500/40 transition-all flex flex-col justify-between space-y-4 group"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-indigo-950/80 border border-indigo-500/20 flex items-center justify-center">
                      <FolderGit2 className="w-4 h-4 text-indigo-400" />
                    </div>
                    <h3
                      onClick={() => navigate(`/projects/${proj.id}`)}
                      className="font-bold text-white text-sm hover:text-indigo-400 cursor-pointer transition-colors"
                    >
                      {proj.name}
                    </h3>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-mono ${
                    proj.status === 'active' ? 'bg-emerald-950/50 text-emerald-400 border border-emerald-800/40' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {proj.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {proj.description || 'No description provided.'}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-1.5 font-mono">
                  <GitBranch className="w-3.5 h-3.5 text-indigo-400" />
                  {proj.repositories.length} Repositories
                </div>

                <div className="flex items-center gap-2">
                  {proj.status === 'active' && (
                    <button
                      onClick={() => archiveProject(proj.id)}
                      className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-amber-400"
                      title="Archive Project"
                    >
                      <Archive className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <button
                    onClick={() => deleteProject(proj.id)}
                    className="p-1.5 rounded-lg hover:bg-rose-500/10 text-slate-400 hover:text-rose-400"
                    title="Delete Project"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => navigate(`/projects/${proj.id}`)}
                    className="p-1.5 rounded-lg bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/40"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
