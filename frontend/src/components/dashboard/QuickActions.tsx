import React from 'react';
import { Code2, Cpu, BrainCircuit, Wrench } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const QuickActions: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-4">
      <h2 className="text-sm font-semibold text-slate-300">Quick Platform Actions</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          onClick={() => navigate('/workspace')}
          className="p-4 rounded-xl glass-card text-left space-y-2 hover:border-indigo-500/40 group"
        >
          <Code2 className="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />
          <div className="text-xs font-semibold text-slate-200">Open Code Editor</div>
          <div className="text-[11px] text-slate-400">View Monaco editor & AI chat</div>
        </button>

        <button
          onClick={() => navigate('/agents')}
          className="p-4 rounded-xl glass-card text-left space-y-2 hover:border-cyan-500/40 group"
        >
          <Cpu className="w-5 h-5 text-cyan-400 group-hover:scale-110 transition-transform" />
          <div className="text-xs font-semibold text-slate-200">Agent Monitor</div>
          <div className="text-[11px] text-slate-400">View multi-agent graph trace</div>
        </button>

        <button
          onClick={() => navigate('/memory')}
          className="p-4 rounded-xl glass-card text-left space-y-2 hover:border-purple-500/40 group"
        >
          <BrainCircuit className="w-5 h-5 text-purple-400 group-hover:scale-110 transition-transform" />
          <div className="text-xs font-semibold text-slate-200">Memory Center</div>
          <div className="text-[11px] text-slate-400">Manage user & repo memory</div>
        </button>

        <button
          onClick={() => navigate('/tools')}
          className="p-4 rounded-xl glass-card text-left space-y-2 hover:border-emerald-500/40 group"
        >
          <Wrench className="w-5 h-5 text-emerald-400 group-hover:scale-110 transition-transform" />
          <div className="text-xs font-semibold text-slate-200">Tool Activity</div>
          <div className="text-[11px] text-slate-400">Inspect 5 read-only tool adapters</div>
        </button>
      </div>
    </div>
  );
};
