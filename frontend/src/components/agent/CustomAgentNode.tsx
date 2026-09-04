import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Sparkles, Layers, Search, ShieldCheck, Database, Wrench, AlertCircle } from 'lucide-react';

const iconMap: Record<string, any> = {
  supervisor: Sparkles,
  planner: Layers,
  context: Search,
  reviewer: ShieldCheck,
  memory: Database,
  tool: Wrench,
};

export const CustomAgentNode = memo(({ data }: any) => {
  const Icon = iconMap[data.agentType] || Sparkles;

  const statusColors: Record<string, string> = {
    active: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    online: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
    idle: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
    error: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
  };

  return (
    <div
      className={`px-4 py-3 rounded-2xl bg-slate-900/90 border backdrop-blur-md shadow-2xl min-w-[180px] transition-all ${
        data.isSelected ? 'border-indigo-500 shadow-glow ring-2 ring-indigo-500/30' : 'border-slate-800 hover:border-slate-700'
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-indigo-500 !w-2.5 !h-2.5" />

      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Icon className="w-4 h-4" />
          </div>
          <span className="font-bold text-xs text-white">{data.label}</span>
        </div>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full border font-mono capitalize ${
            statusColors[data.status] || statusColors.online
          }`}
        >
          {data.status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-2 border-t border-slate-800">
        <div>
          <span className="text-slate-500 block">Duration</span>
          <span className="text-cyan-400 font-semibold">{data.duration}ms</span>
        </div>
        <div>
          <span className="text-slate-500 block">Confidence</span>
          <span className="text-emerald-400 font-semibold">{(data.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>

      {data.errors > 0 && (
        <div className="mt-2 text-[10px] text-rose-400 flex items-center gap-1 font-mono">
          <AlertCircle className="w-3 h-3" />
          <span>{data.errors} error(s) detected</span>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-indigo-500 !w-2.5 !h-2.5" />
    </div>
  );
});

CustomAgentNode.displayName = 'CustomAgentNode';
