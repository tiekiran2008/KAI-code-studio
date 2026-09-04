import React, { useState } from 'react';
import { useTools } from '../hooks/useTools';
import { LoadingScreen } from '../components/common/LoadingScreen';
import { 
  Wrench, 
  Clock, 
  CheckCircle2, 
  Terminal, 
  Code 
} from 'lucide-react';

export const ToolActivityPage: React.FC = () => {
  const { tools, isLoading } = useTools();
  const [activeTab, setActiveTab] = useState<'catalog' | 'audit'>('catalog');

  const mockAuditLogs = [
    {
      id: 'log-1',
      toolName: 'local_fs_read',
      callerAgent: 'SupervisorAgent',
      arguments: { action: 'read_file', path: 'backend/src/application/agents/supervisor.py' },
      status: 'success',
      latencyMs: 14.2,
      retryCount: 0,
      timestamp: '2026-07-29T18:01:03Z'
    },
    {
      id: 'log-2',
      toolName: 'github_read',
      callerAgent: 'SupervisorAgent',
      arguments: { owner: 'kelum', repo: 'AI-Agent', action: 'branches' },
      status: 'success',
      latencyMs: 185.0,
      retryCount: 0,
      timestamp: '2026-07-29T17:45:10Z'
    },
    {
      id: 'log-3',
      toolName: 'repo_diff',
      callerAgent: 'SupervisorAgent',
      arguments: { action: 'summary', base: 'main', head: 'dev' },
      status: 'success',
      latencyMs: 42.1,
      retryCount: 0,
      timestamp: '2026-07-29T16:20:00Z'
    }
  ];

  if (isLoading) {
    return <LoadingScreen isLoading={true} message="Loading tool activity framework..." fullScreen={false} />;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Wrench className="w-5 h-5 text-emerald-400" /> Tool Calling Framework & Audit Activity
          </h1>
          <p className="text-xs text-slate-400">
            Monitors safe read-only tool adapters, RBAC permission enforcement, timeouts, and execution retries.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === 'catalog'
                ? 'bg-emerald-600 text-white shadow-glow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Wrench className="w-4 h-4" /> Tool Catalog ({tools.length})
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              activeTab === 'audit'
                ? 'bg-emerald-600 text-white shadow-glow'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Terminal className="w-4 h-4" /> Audit Feed
          </button>
        </div>
      </div>

      {/* Catalog View */}
      {activeTab === 'catalog' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tools.map((tool) => (
            <div
              key={tool.name}
              className="glass-card p-5 rounded-2xl space-y-4 border border-slate-800 hover:border-emerald-500/40"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm font-bold text-emerald-300 flex items-center gap-2">
                  <Code className="w-4 h-4 text-emerald-400" /> {tool.name}
                </span>

                <span
                  className={`text-[10px] px-2.5 py-0.5 rounded-full font-mono uppercase border ${
                    tool.permissions === 'read_only'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : tool.permissions === 'restricted'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}
                >
                  {tool.permissions}
                </span>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed min-h-[36px]">
                {tool.description}
              </p>

              <div className="p-3 rounded-xl bg-slate-950 font-mono text-[11px] text-slate-400 border border-slate-800 space-y-1">
                <div className="text-[10px] text-indigo-400 font-semibold uppercase">Input Parameters Schema</div>
                <pre className="text-slate-300 text-[10px] overflow-x-auto">
                  {JSON.stringify(tool.inputSchema, null, 2)}
                </pre>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-cyan-400" /> Timeout: {tool.timeoutSeconds}s
                </span>
                <span>Max Retries: {tool.retryMax}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Audit Feed View */}
      {activeTab === 'audit' && (
        <div className="glass-panel p-6 rounded-2xl space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="text-xs uppercase bg-slate-900/80 text-slate-400 border-b border-slate-800 font-mono">
                <tr>
                  <th className="px-4 py-3">Tool Name</th>
                  <th className="px-4 py-3">Caller Agent</th>
                  <th className="px-4 py-3">Arguments JSON</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Retries</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                {mockAuditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-4 py-4 font-bold text-emerald-300">{log.toolName}</td>
                    <td className="px-4 py-4 text-indigo-300">{log.callerAgent}</td>
                    <td className="px-4 py-4 text-slate-400 max-w-xs truncate">
                      {JSON.stringify(log.arguments)}
                    </td>
                    <td className="px-4 py-4 text-cyan-400">{log.latencyMs} ms</td>
                    <td className="px-4 py-4">{log.retryCount}</td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1 text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="w-3 h-3" /> Success
                      </span>
                    </td>
                    <td className="px-4 py-4 text-right text-slate-500">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
