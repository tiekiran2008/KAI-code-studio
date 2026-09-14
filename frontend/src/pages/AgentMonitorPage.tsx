import React, { useState } from 'react';
import { Cpu, Activity } from 'lucide-react';
import { AgentFlowGraph } from '../components/agent/AgentFlowGraph';
import { AgentDetailsPanel } from '../components/agent/AgentDetailsPanel';
import { FocusAura } from '../components/ambient/FocusAura';

export const AgentMonitorPage: React.FC = () => {
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>('supervisor');

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Overview Banner */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Cpu className="w-5 h-5 text-indigo-400" /> Multi-Agent Execution Topography
          </h1>
          <p className="text-xs text-slate-400">
            Real-time observability into the LangGraph agents powering autonomous software engineering.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" /> LangGraph Status: Healthy
          </div>
        </div>
      </div>

      {/* React Flow Interactive Graph */}
      <FocusAura area="agent" className="glass-panel p-6 rounded-2xl space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" /> LangGraph Execution Flow (Interactive React Flow)
        </h2>

        <AgentFlowGraph
          selectedAgentId={selectedAgentId}
          onSelectAgent={(id) => setSelectedAgentId(id)}
        />
      </FocusAura>

      {/* Selected Agent Details Panel */}
      <FocusAura area="agent" className="rounded-2xl overflow-hidden">
        <AgentDetailsPanel selectedAgentId={selectedAgentId} />
      </FocusAura>
    </div>
  );
};
