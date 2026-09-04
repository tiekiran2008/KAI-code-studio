import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { ChevronDown, Layers, Check, Plus, Settings } from 'lucide-react';

export const WorkspaceSwitcher: React.FC = () => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { workspaces, activeWorkspaceId, setActiveWorkspace, fetchWorkspaces } = useWorkspaceStore();
  const activeWorkspace = workspaces.find(w => w.id === activeWorkspaceId);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSelect = (id: string) => {
    setActiveWorkspace(id);
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all ${
          open
            ? 'bg-indigo-900/40 border-indigo-500/50 text-indigo-200'
            : 'bg-slate-900 border-slate-700/80 text-slate-300 hover:border-slate-600 hover:text-white'
        }`}
      >
        <div className="w-5 h-5 rounded-md bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
          <Layers className="w-3 h-3 text-white" />
        </div>
        <span className="max-w-[120px] truncate">
          {activeWorkspace ? activeWorkspace.name : 'No Workspace'}
        </span>
        <ChevronDown className={`w-3 h-3 transition-transform text-slate-500 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute top-full mt-2 left-0 w-64 bg-[#0c1222] border border-slate-700/80 rounded-2xl shadow-2xl shadow-black/40 z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-800/60">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Switch Workspace</p>
          </div>

          {/* List */}
          <div className="max-h-52 overflow-y-auto py-2">
            {workspaces.length === 0 ? (
              <p className="text-slate-500 text-xs text-center py-4">No workspaces yet</p>
            ) : (
              workspaces.map(ws => (
                <button
                  key={ws.id}
                  onClick={() => handleSelect(ws.id)}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/60 transition-colors text-left ${
                    ws.id === activeWorkspaceId ? 'bg-indigo-500/10' : ''
                  }`}
                >
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center shrink-0">
                    <Layers className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-white font-medium truncate">{ws.name}</p>
                    <p className="text-xs text-slate-500">{ws.repo_count} repositories</p>
                  </div>
                  {ws.id === activeWorkspaceId && <Check className="w-3.5 h-3.5 text-indigo-400 shrink-0" />}
                </button>
              ))
            )}
          </div>

          {/* Footer actions */}
          <div className="border-t border-slate-800/60 p-2 flex flex-col gap-1">
            <button
              onClick={() => { navigate('/workspaces/new'); setOpen(false); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 rounded-xl transition-all"
            >
              <Plus className="w-3.5 h-3.5" /> New Workspace
            </button>
            <button
              onClick={() => { navigate('/workspaces'); setOpen(false); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-xl transition-all"
            >
              <Settings className="w-3.5 h-3.5" /> Manage Workspaces
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
