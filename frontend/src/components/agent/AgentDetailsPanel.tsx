import React from 'react';
import { 
  Sparkles, 
  Layers, 
  Search, 
  ShieldCheck, 
  Database, 
  Wrench, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Activity 
} from 'lucide-react';

interface AgentMetrics {
  id: string;
  name: string;
  role: string;
  status: 'active' | 'online' | 'idle' | 'error';
  duration: number;
  confidence: number;
  errorsCount: number;
  timeline: { step: string; latency: number; status: 'ok' | 'error'; timestamp: string }[];
  errorLog?: string[];
}

const AGENT_DATA: Record<string, AgentMetrics> = {
  supervisor: {
    id: 'supervisor',
    name: 'Supervisor Agent',
    role: 'Orchestrates the LangGraph multi-agent execution, coordinates planner, context, reviewer, memory, and tool agents.',
    status: 'active',
    duration: 180,
    confidence: 0.98,
    errorsCount: 0,
    timeline: [
      { step: 'Parsed initial user architecture query', latency: 12, status: 'ok', timestamp: '12:45:01' },
      { step: 'Delegated task decomposition to Planner', latency: 15, status: 'ok', timestamp: '12:45:02' },
      { step: 'Synthesized final multi-agent response', latency: 153, status: 'ok', timestamp: '12:45:05' },
    ],
  },
  planner: {
    id: 'planner',
    name: 'Planner Agent',
    role: 'Formulates task execution DAGs, breaks complex instructions into subtasks, and assigns agent routes.',
    status: 'online',
    duration: 240,
    confidence: 0.95,
    errorsCount: 0,
    timeline: [
      { step: 'Received subtask decomposition request', latency: 20, status: 'ok', timestamp: '12:45:02' },
      { step: 'Formulated parallel branch graph', latency: 220, status: 'ok', timestamp: '12:45:03' },
    ],
  },
  context: {
    id: 'context',
    name: 'Context Agent',
    role: 'Queries RAG vector store & BM25 indices to retrieve exact source code snippets for LLM reasoning context.',
    status: 'online',
    duration: 85,
    confidence: 0.96,
    errorsCount: 0,
    timeline: [
      { step: 'Performed hybrid RRF retrieval', latency: 45, status: 'ok', timestamp: '12:45:03' },
      { step: 'Formatted citation snippets', latency: 40, status: 'ok', timestamp: '12:45:04' },
    ],
  },
  reviewer: {
    id: 'reviewer',
    name: 'Code Reviewer Agent',
    role: 'Performs static code checks, OWASP security analysis, AST inspection, and logic validation.',
    status: 'online',
    duration: 210,
    confidence: 0.94,
    errorsCount: 1,
    timeline: [
      { step: 'AST dependency graph check', latency: 90, status: 'ok', timestamp: '12:45:04' },
      { step: 'OWASP vulnerability scanning', latency: 120, status: 'error', timestamp: '12:45:04' },
    ],
    errorLog: ['Warn: Null pointer potential on line 142 of supervisor.py'],
  },
  memory: {
    id: 'memory',
    name: 'Memory Agent',
    role: 'Retrieves user preferences, project tech stack memory, and episodic conversation context.',
    status: 'online',
    duration: 120,
    confidence: 0.97,
    errorsCount: 0,
    timeline: [
      { step: 'Semantic memory lookup in PGVector', latency: 80, status: 'ok', timestamp: '12:45:03' },
      { step: 'Recency score decay calculation', latency: 40, status: 'ok', timestamp: '12:45:04' },
    ],
  },
  tool: {
    id: 'tool',
    name: 'Tool Adapter Agent',
    role: 'Executes read-only sandbox system commands, file system reads, and terminal output parsing.',
    status: 'online',
    duration: 150,
    confidence: 0.99,
    errorsCount: 0,
    timeline: [
      { step: 'Invoked read_file adapter', latency: 50, status: 'ok', timestamp: '12:45:04' },
      { step: 'Validated JSON response schema', latency: 100, status: 'ok', timestamp: '12:45:05' },
    ],
  },
};

const iconMap: Record<string, any> = {
  supervisor: Sparkles,
  planner: Layers,
  context: Search,
  reviewer: ShieldCheck,
  memory: Database,
  tool: Wrench,
};

interface AgentDetailsPanelProps {
  selectedAgentId: string | null;
}

export const AgentDetailsPanel: React.FC<AgentDetailsPanelProps> = ({ selectedAgentId }) => {
  const agentId = selectedAgentId || 'supervisor';
  const agent = AGENT_DATA[agentId] || AGENT_DATA.supervisor;
  const Icon = iconMap[agent.id] || Sparkles;

  return (
    <div className="glass-panel p-6 rounded-2xl space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Icon className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">{agent.name}</h2>
            <p className="text-xs text-slate-400">{agent.role}</p>
          </div>
        </div>

        <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono capitalize">
          {agent.status}
        </span>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-card p-4 rounded-xl space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <Clock className="w-3.5 h-3.5 text-cyan-400" /> Duration (P95)
          </span>
          <div className="text-xl font-bold text-white font-mono">{agent.duration} ms</div>
        </div>

        <div className="glass-card p-4 rounded-xl space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Confidence
          </span>
          <div className="text-xl font-bold text-white font-mono">{(agent.confidence * 100).toFixed(0)}%</div>
        </div>

        <div className="glass-card p-4 rounded-xl space-y-1">
          <span className="text-xs text-slate-400 flex items-center gap-1">
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" /> Total Errors
          </span>
          <div className="text-xl font-bold text-white font-mono">{agent.errorsCount}</div>
        </div>
      </div>

      {/* Error Logs if present */}
      {agent.errorLog && agent.errorLog.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-rose-400 flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5" /> Recent Diagnostic Warnings & Errors
          </h3>
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 font-mono text-xs text-rose-200 space-y-1">
            {agent.errorLog.map((err, i) => (
              <div key={i}>{err}</div>
            ))}
          </div>
        </div>
      )}

      {/* Execution Timeline */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-indigo-400" /> Agent Step Timeline
        </h3>

        <div className="space-y-2">
          {agent.timeline.map((item, idx) => (
            <div
              key={idx}
              className="p-3 rounded-xl glass-card flex items-center justify-between text-xs font-mono"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    item.status === 'ok' ? 'bg-emerald-400' : 'bg-rose-400'
                  }`}
                />
                <span className="text-slate-200">{item.step}</span>
              </div>

              <div className="flex items-center gap-4 text-slate-400">
                <span>{item.latency}ms</span>
                <span className="text-[10px] text-slate-500">{item.timestamp}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
