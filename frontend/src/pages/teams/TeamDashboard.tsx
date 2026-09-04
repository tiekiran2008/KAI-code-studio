import React, { useEffect } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { Users, Shield, Clock, Activity, UserPlus } from 'lucide-react';

export const TeamDashboard: React.FC = () => {
  const { activeTeam, auditLogs, fetchAuditLogs, isLoading } = useTeamStore();

  useEffect(() => {
    if (activeTeam) {
      fetchAuditLogs(activeTeam.id);
    }
  }, [activeTeam, fetchAuditLogs]);

  if (isLoading && !activeTeam) {
    return <div className="flex h-full items-center justify-center text-gray-500">Loading team...</div>;
  }

  if (!activeTeam) {
    return (
      <div className="flex flex-col h-full items-center justify-center p-8 text-center animate-in fade-in">
        <div className="bg-gray-800/50 p-6 rounded-full mb-6 ring-1 ring-gray-700/50">
          <Users className="w-12 h-12 text-gray-400" />
        </div>
        <h2 className="text-2xl font-semibold text-white mb-2">No Active Team</h2>
        <p className="text-gray-400 max-w-md">
          You need to create or select a team to access the team dashboard.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 backdrop-blur-sm">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            {activeTeam.name}
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
              Team
            </span>
          </h1>
          {activeTeam.description && (
            <p className="text-gray-400 mt-2">{activeTeam.description}</p>
          )}
        </div>
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors">
            <UserPlus className="w-4 h-4" />
            Invite Member
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 flex flex-col">
          <div className="flex items-center gap-3 text-gray-400 mb-4">
            <Users className="w-5 h-5 text-indigo-400" />
            <h3 className="font-medium">Total Members</h3>
          </div>
          <span className="text-3xl font-bold text-white">{activeTeam.member_count}</span>
          <p className="text-sm text-gray-500 mt-2">Active members in the team</p>
        </div>
        
        <div className="bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 flex flex-col">
          <div className="flex items-center gap-3 text-gray-400 mb-4">
            <Shield className="w-5 h-5 text-emerald-400" />
            <h3 className="font-medium">Roles & Permissions</h3>
          </div>
          <span className="text-3xl font-bold text-white">6</span>
          <p className="text-sm text-gray-500 mt-2">Configurable access roles</p>
        </div>

        <div className="bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 flex flex-col">
          <div className="flex items-center gap-3 text-gray-400 mb-4">
            <Clock className="w-5 h-5 text-amber-400" />
            <h3 className="font-medium">Team Created</h3>
          </div>
          <span className="text-xl font-bold text-white">
            {new Date(activeTeam.created_at).toLocaleDateString(undefined, { 
              year: 'numeric', month: 'long', day: 'numeric' 
            })}
          </span>
          <p className="text-sm text-gray-500 mt-2">Since inception</p>
        </div>
      </div>

      <div className="flex-1 bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 flex flex-col overflow-hidden">
        <div className="flex items-center gap-3 text-gray-400 mb-6">
          <Activity className="w-5 h-5 text-rose-400" />
          <h3 className="font-medium text-white">Recent Audit Logs</h3>
        </div>
        
        <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
          {auditLogs.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No recent activity found.
            </div>
          ) : (
            <div className="space-y-4">
              {auditLogs.slice(0, 10).map((log) => (
                <div key={log.id} className="flex gap-4 items-start p-4 bg-gray-800/30 rounded-xl border border-gray-700/30">
                  <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center shrink-0">
                    <span className="text-xs font-medium text-gray-300">
                      {log.actor_id.substring(0, 2).toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-300">
                      <span className="font-medium text-white">{log.actor_id}</span> performed{' '}
                      <span className="font-medium text-indigo-400">{log.action}</span> on{' '}
                      <span className="font-medium text-gray-400">{log.target_type}</span>
                    </p>
                    {log.target_id && (
                      <p className="text-xs text-gray-500 mt-1">Target ID: {log.target_id}</p>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
