import React, { useEffect, useState } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { TeamHeaderNav } from './TeamHeaderNav';
import { CreateTeamModal } from './CreateTeamModal';
import { InviteMemberModal } from './InviteMemberModal';
import {
  Users,
  Shield,
  Clock,
  Activity,
  UserPlus,
  Plus,
  Building2,
  FolderGit2,
  ArrowRight,
  Sparkles,
  CheckCircle2
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const TeamDashboard: React.FC = () => {
  const { teams, activeTeam, auditLogs, fetchAuditLogs, setActiveTeam, isLoading, fetchTeams } = useTeamStore();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  useEffect(() => {
    if (activeTeam) {
      fetchAuditLogs(activeTeam.id);
    }
  }, [activeTeam, fetchAuditLogs]);

  // Loading state when initial teams fetch
  if (isLoading && teams.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-slate-400">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full border-2 border-indigo-500/30 border-t-indigo-500 animate-spin" />
          <span>Loading teams...</span>
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // EMPTY STATE 1: Zero teams exist in the system
  // --------------------------------------------------------------------------
  if (teams.length === 0) {
    return (
      <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center glass-panel rounded-2xl max-w-2xl mx-auto my-auto w-full">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center mb-6 shadow-xl shadow-indigo-500/20">
            <Users className="w-8 h-8 text-white" />
          </div>
          
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Create Your First Team</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-md mb-8 leading-relaxed">
            Collaborate with your organization members on shared repositories, code reviews, and autonomous AI agents with fine-grained role-based access control.
          </p>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl transition-all shadow-lg shadow-indigo-600/30 hover:scale-[1.02] active:scale-[0.98]"
          >
            <Plus className="w-5 h-5" />
            Create Team
          </button>
        </div>

        <CreateTeamModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
        />
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // EMPTY STATE 2: Teams exist, but no team is currently active
  // --------------------------------------------------------------------------
  if (!activeTeam) {
    return (
      <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
        <TeamHeaderNav />

        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center max-w-3xl mx-auto w-full">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex items-center justify-center mb-4">
            <Building2 className="w-7 h-7" />
          </div>
          
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">Select a Team</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-md mb-8">
            Choose an existing team from below or create a new one to view members, activity logs, and settings.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full mb-6">
            {teams.map((t) => (
              <div
                key={t.id}
                onClick={() => setActiveTeam(t)}
                className="group cursor-pointer glass-card hover:border-indigo-500/50 p-5 rounded-2xl text-left transition-all duration-200 hover:shadow-xl hover:shadow-indigo-500/10 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-300 transition-colors">
                      {t.name}
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {t.member_count} member{t.member_count !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2 mb-4">
                    {t.description || 'No description provided.'}
                  </p>
                </div>
                <div className="flex items-center text-xs font-medium text-indigo-600 dark:text-indigo-400 group-hover:text-indigo-700 dark:group-hover:text-indigo-300">
                  <span>Open Team Dashboard</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1 transition-transform group-hover:translate-x-1" />
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-500/60 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            Create Another Team
          </button>
        </div>

        <CreateTeamModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
        />
      </div>
    );
  }

  // --------------------------------------------------------------------------
  // ACTIVE TEAM DASHBOARD
  // --------------------------------------------------------------------------
  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
      <TeamHeaderNav />

      {/* Hero Overview Banner */}
      <div className="glass-panel flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              {activeTeam.name}
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/30">
              Active Organization
            </span>
          </div>
          <p className="text-slate-600 dark:text-slate-400 text-sm mt-1.5 max-w-2xl">
            {activeTeam.description || 'No description provided for this team.'}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => setIsInviteModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-indigo-600/20"
          >
            <UserPlus className="w-4 h-4" />
            Invite Member
          </button>
          <Link
            to="/teams/members"
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300/80 text-slate-700 hover:text-slate-900 dark:bg-slate-800/80 dark:hover:bg-slate-700/80 dark:border-slate-700 dark:text-slate-200 dark:hover:text-white rounded-xl text-sm font-medium transition-colors"
          >
            <Users className="w-4 h-4 text-slate-500 dark:text-slate-400" />
            View Members
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-5 rounded-2xl flex flex-col">
          <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 mb-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              <Users className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Total Members</h3>
          </div>
          <span className="text-3xl font-bold text-slate-900 dark:text-white">{activeTeam.member_count}</span>
          <p className="text-xs text-slate-500 mt-2">Active collaborators in team</p>
        </div>

        <div className="glass-card p-5 rounded-2xl flex flex-col">
          <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 mb-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
              <Shield className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">RBAC Roles</h3>
          </div>
          <span className="text-3xl font-bold text-slate-900 dark:text-white">6</span>
          <p className="text-xs text-slate-500 mt-2">Configurable permission tiers</p>
        </div>

        <div className="glass-card p-5 rounded-2xl flex flex-col">
          <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 mb-3">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
              <FolderGit2 className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Collaborative Workspaces</h3>
          </div>
          <span className="text-3xl font-bold text-slate-900 dark:text-white">Active</span>
          <p className="text-xs text-slate-500 mt-2">Shared workspace access</p>
        </div>

        <div className="glass-card p-5 rounded-2xl flex flex-col">
          <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400 mb-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
              <Clock className="w-4 h-4" />
            </div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Created On</h3>
          </div>
          <span className="text-base font-bold text-slate-900 dark:text-white mt-1">
            {new Date(activeTeam.created_at).toLocaleDateString(undefined, {
              year: 'numeric',
              month: 'short',
              day: 'numeric'
            })}
          </span>
          <p className="text-xs text-slate-500 mt-2">Team inception date</p>
        </div>
      </div>

      {/* Main Content Grid: Members Preview + Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        
        {/* Members Preview */}
        <div className="lg:col-span-1 glass-card p-5 rounded-2xl flex flex-col overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Team Members</h3>
            </div>
            <Link
              to="/teams/members"
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium"
            >
              View All ({activeTeam.members.length})
            </Link>
          </div>

          <div className="space-y-2.5 overflow-y-auto custom-scrollbar flex-1 pr-1">
            {activeTeam.members.slice(0, 6).map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200/80 hover:border-slate-300 dark:bg-slate-900/60 dark:border-slate-800/60 dark:hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 font-semibold text-xs flex items-center justify-center shrink-0 border border-indigo-500/30">
                    {(m.name || m.user_id).substring(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-slate-900 dark:text-white truncate">{m.name || m.user_id}</p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">{m.email || m.user_id}</p>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-medium capitalize bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shrink-0 ml-2">
                  {m.role}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Audit Logs */}
        <div className="lg:col-span-2 glass-card p-5 rounded-2xl flex flex-col overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-rose-500 dark:text-rose-400" />
              <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Recent Team Activity</h3>
            </div>
            <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
              {auditLogs.length} event{auditLogs.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto custom-scrollbar pr-1 space-y-2.5">
            {auditLogs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
                <Activity className="w-8 h-8 text-slate-400 dark:text-slate-600 mb-2 opacity-40" />
                <p className="text-xs">No recent activity logs recorded for this team.</p>
              </div>
            ) : (
              auditLogs.slice(0, 12).map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-3 p-3 rounded-xl bg-slate-50 border border-slate-200/80 dark:bg-slate-900/40 dark:border-slate-800/60"
                >
                  <div className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 flex items-center justify-center shrink-0 text-[10px] font-mono border border-slate-200 dark:border-slate-700">
                    {log.actor_id.substring(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-700 dark:text-slate-200">
                      <span className="font-medium text-slate-900 dark:text-white">{log.actor_id}</span>{' '}
                      <span className="text-indigo-600 dark:text-indigo-400 font-medium">{log.action}</span> on{' '}
                      <span className="text-slate-700 dark:text-slate-300 font-medium">{log.target_type}</span>
                    </p>
                    {log.target_id && (
                      <p className="text-[11px] text-slate-500 mt-0.5 font-mono">ID: {log.target_id}</p>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

      </div>

      <InviteMemberModal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
      />
    </div>
  );
};
