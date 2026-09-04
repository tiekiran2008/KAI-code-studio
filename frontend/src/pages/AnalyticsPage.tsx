import React from 'react';
import { useAnalytics } from '../hooks/useAnalytics';
import { LoadingScreen } from '../components/common/LoadingScreen';
import { 
  BarChart3, 
  Zap, 
  Cpu, 
  BrainCircuit, 
  Activity 
} from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const { analytics, isLoading } = useAnalytics();

  if (isLoading || !analytics) {
    return <LoadingScreen isLoading={true} message="Loading platform analytics..." fullScreen={false} />;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-cyan-400" /> Platform Telemetry & Analytics
          </h1>
          <p className="text-xs text-slate-400">
            Performance metrics covering RAG retrieval latency, LLM token consumption, agent timings, and memory caching hit rates.
          </p>
        </div>

        <div className="px-3 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs font-mono flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400 animate-pulse" /> Live Telemetry Pipeline
        </div>
      </div>

      {/* Latency Cards Suite */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card p-5 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>RAG Retrieval P50 Latency</span>
            <Zap className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">{analytics.retrievalLatencyP50} ms</div>
          <div className="text-[11px] text-emerald-400 font-mono">BM25 Keyword Match</div>
        </div>

        <div className="glass-card p-5 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>RAG Retrieval P95 Latency</span>
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">{analytics.retrievalLatencyP95} ms</div>
          <div className="text-[11px] text-cyan-400 font-mono">Qdrant Vector Hybrid RRF</div>
        </div>

        <div className="glass-card p-5 rounded-2xl space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>RAG Retrieval P99 Latency</span>
            <Zap className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-3xl font-bold text-white font-mono">{analytics.retrievalLatencyP99} ms</div>
          <div className="text-[11px] text-purple-400 font-mono">Cross-Encoder Rerank</div>
        </div>
      </div>

      {/* Grid: Tokens & Agents metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-400" /> Agent Execution Breakdown
          </h2>

          <div className="space-y-3 font-mono text-xs">
            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>Supervisor Agent (Orchestration & Tool Synthesis)</span>
                <span>180 ms</span>
              </div>
              <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                <div className="h-full bg-purple-500 rounded-full" style={{ width: '45%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>Planner Agent (Task Decomposition)</span>
                <span>240 ms</span>
              </div>
              <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-500 rounded-full" style={{ width: '60%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>Security Review Agent (OWASP Scans)</span>
                <span>220 ms</span>
              </div>
              <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                <div className="h-full bg-rose-500 rounded-full" style={{ width: '55%' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex justify-between text-slate-300">
                <span>Context Agent (Dense RAG Retrieval)</span>
                <span>85 ms</span>
              </div>
              <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-500 rounded-full" style={{ width: '22%' }} />
              </div>
            </div>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <h2 className="text-base font-semibold text-white flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-purple-400" /> Memory & Token Metrics
          </h2>

          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-4 rounded-xl space-y-1">
              <div className="text-xs text-slate-400">Total Tokens Consumed</div>
              <div className="text-xl font-bold text-white font-mono">
                {analytics.totalTokensUsed.toLocaleString()}
              </div>
            </div>

            <div className="glass-card p-4 rounded-xl space-y-1">
              <div className="text-xs text-slate-400">Memory Hit Rate</div>
              <div className="text-xl font-bold text-emerald-400 font-mono">
                {(analytics.memoryHitRate * 100).toFixed(1)}%
              </div>
            </div>

            <div className="glass-card p-4 rounded-xl space-y-1">
              <div className="text-xs text-slate-400">Tool Invocations</div>
              <div className="text-xl font-bold text-cyan-400 font-mono">
                {analytics.toolInvocationsCount}
              </div>
            </div>

            <div className="glass-card p-4 rounded-xl space-y-1">
              <div className="text-xs text-slate-400">Agent Executions</div>
              <div className="text-xl font-bold text-purple-400 font-mono">
                {analytics.agentExecutionsCount}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
