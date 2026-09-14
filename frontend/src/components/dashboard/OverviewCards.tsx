import React from 'react';
import { GitBranch, Zap, BrainCircuit, Cpu, CheckCircle2, Clock, Database } from 'lucide-react';
import { AnalyticsMetrics } from '../../types';

interface OverviewCardsProps {
  repoCount: number;
  analytics?: AnalyticsMetrics;
}

export const OverviewCards: React.FC<OverviewCardsProps> = ({ repoCount, analytics }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="glass-card p-5 rounded-2xl space-y-2">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Indexed Repositories</span>
          <GitBranch className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="text-2xl font-bold text-white">{repoCount} Repos</div>
        <div className="text-[11px] text-emerald-400 flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5" /> Ready for analysis
        </div>
      </div>

      <div className="glass-card p-5 rounded-2xl space-y-2">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>RAG Retrieval P95</span>
          <Zap className="w-4 h-4 text-cyan-400" />
        </div>
        <div className="text-2xl font-bold text-white">
          {analytics?.retrievalLatencyP95 ? `${analytics.retrievalLatencyP95.toFixed(1)} ms` : '---'}
        </div>
        <div className="text-[11px] text-slate-400 flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-cyan-400" /> Hybrid BM25 + Vector RRF
        </div>
      </div>

      <div className="glass-card p-5 rounded-2xl space-y-2">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Memory Hit Rate</span>
          <BrainCircuit className="w-4 h-4 text-purple-400" />
        </div>
        <div className="text-2xl font-bold text-white">
          {analytics?.memoryHitRate !== undefined && analytics.memoryHitRate !== null
            ? `${(analytics.memoryHitRate > 1 ? analytics.memoryHitRate : analytics.memoryHitRate * 100).toFixed(1)}%`
            : '---'}
        </div>
        <div className="text-[11px] text-purple-400 flex items-center gap-1">
          <Database className="w-3.5 h-3.5" /> Episodic & Semantic
        </div>
      </div>

      <div className="glass-card p-5 rounded-2xl space-y-2">
        <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
          <span>Agent Confidence</span>
          <Cpu className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="text-2xl font-bold text-white">
          {analytics?.averageConfidence !== undefined && analytics.averageConfidence !== null
            ? `${(analytics.averageConfidence > 1 ? analytics.averageConfidence : analytics.averageConfidence * 100).toFixed(1)}%`
            : '---'}
        </div>
        <div className="text-[11px] text-emerald-400 flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5" /> Evaluation Passed
        </div>
      </div>
    </div>
  );
};
