import React, { useEffect, useState } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { TeamHeaderNav } from './TeamHeaderNav';
import { Mail, Clock, Shield, X, Search, Plus, Users } from 'lucide-react';
import { InviteMemberModal } from './InviteMemberModal';
import { CreateTeamModal } from './CreateTeamModal';

export const PendingInvitationsPage: React.FC = () => {
  const { activeTeam, teamInvitations, fetchTeamInvitations } = useTeamStore();
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (activeTeam) {
      fetchTeamInvitations(activeTeam.id);
    }
  }, [activeTeam, fetchTeamInvitations]);

  if (!activeTeam) {
    return (
      <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
        <TeamHeaderNav />
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center glass-panel rounded-2xl">
          <Users className="w-12 h-12 text-slate-400 dark:text-slate-600 mb-3" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">No Active Team Selected</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-sm mb-6">
            Please select or create a team using the team switcher above to manage pending invitations.
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
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

  const pendingInvites = teamInvitations.filter(i => i.status === 'pending');
  const filteredInvites = pendingInvites.filter(i => 
    i.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
      <TeamHeaderNav />

      <div className="glass-panel flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">Pending Invitations</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">Manage sent invitations and invite new colleagues to {activeTeam.name}.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search invitations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700/60 rounded-xl text-sm text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500/60 w-60"
            />
          </div>
          <button 
            onClick={() => setIsInviteModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors shrink-0"
          >
            <Mail className="w-4 h-4" />
            Invite Member
          </button>
        </div>
      </div>

      <div className="flex-1 glass-card rounded-2xl overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800/80 bg-slate-100/75 dark:bg-slate-950/40">
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Email Address</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Role</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Invited By</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Sent On</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60">
              {filteredInvites.map((invite) => (
                <tr key={invite.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 flex items-center justify-center shrink-0">
                        <Mail className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                      </div>
                      <span className="text-sm font-medium text-slate-900 dark:text-white">{invite.email}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      <Shield className="w-3 h-3 text-indigo-600 dark:text-indigo-400" />
                      {invite.role.charAt(0).toUpperCase() + invite.role.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                    {invite.invited_by}
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                    <div className="flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                      {new Date(invite.created_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      className="p-2 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                      title="Revoke Invitation"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {filteredInvites.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="flex flex-col items-center justify-center text-slate-500 gap-3">
                      <Mail className="w-10 h-10 text-slate-400 dark:text-slate-600" />
                      <p className="text-sm">No pending invitations found.</p>
                      <button 
                        onClick={() => setIsInviteModalOpen(true)}
                        className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium mt-1"
                      >
                        Send an invitation
                      </button>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <InviteMemberModal 
        isOpen={isInviteModalOpen} 
        onClose={() => setIsInviteModalOpen(false)} 
      />
    </div>
  );
};
