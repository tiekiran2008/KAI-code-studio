import React, { useState } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { TeamHeaderNav } from './TeamHeaderNav';
import { Search, ShieldAlert, UserX, User, Shield, ChevronDown, Users, Plus } from 'lucide-react';
import { RoleEnum } from '../../types';
import { CreateTeamModal } from './CreateTeamModal';
import { InviteMemberModal } from './InviteMemberModal';

export const TeamMembersPage: React.FC = () => {
  const { activeTeam, changeMemberRole, removeMember } = useTeamStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [editingMember, setEditingMember] = useState<string | null>(null);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  if (!activeTeam) {
    return (
      <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
        <TeamHeaderNav />
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center glass-panel rounded-2xl">
          <Users className="w-12 h-12 text-slate-400 dark:text-slate-600 mb-3" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">No Active Team Selected</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-sm mb-6">
            Please select or create a team using the team switcher above to manage members and roles.
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

  const filteredMembers = activeTeam.members.filter(m => 
    m.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    m.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.user_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const roles: RoleEnum[] = ['owner', 'admin', 'maintainer', 'developer', 'reviewer', 'viewer'];

  const getRoleBadgeColor = (role: RoleEnum) => {
    switch (role) {
      case 'owner': return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20';
      case 'admin': return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
      case 'maintainer': return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20';
      case 'developer': return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20';
      case 'reviewer': return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
      case 'viewer': return 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20';
      default: return 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20';
    }
  };

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
      <TeamHeaderNav />

      <div className="glass-panel flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">Team Members</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">Manage members and their assigned RBAC roles in {activeTeam.name}.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search members..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-900/80 border border-slate-300 dark:border-slate-700/60 rounded-xl text-sm text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500/60 w-60"
            />
          </div>
          <button
            onClick={() => setIsInviteModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
            Invite Member
          </button>
        </div>
      </div>

      <div className="flex-1 glass-card rounded-2xl overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800/80 bg-slate-100/75 dark:bg-slate-950/40">
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Member</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Role</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400">Joined</th>
                <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-400 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60">
              {filteredMembers.map((member) => (
                <tr key={member.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/40 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-500/30 flex items-center justify-center font-bold text-xs shrink-0">
                        {member.avatar ? (
                          <img src={member.avatar} alt={member.name} className="w-full h-full rounded-xl object-cover" />
                        ) : (
                          (member.name || member.user_id).substring(0, 2).toUpperCase()
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-slate-900 dark:text-white truncate">{member.name || member.email || member.user_id}</div>
                        <div className="text-xs text-slate-500 dark:text-slate-400 truncate">{member.email || member.user_id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {editingMember === member.id ? (
                      <div className="relative">
                        <select
                          value={member.role}
                          onChange={(e) => {
                            changeMemberRole(activeTeam.id, member.user_id, e.target.value as RoleEnum);
                            setEditingMember(null);
                          }}
                          onBlur={() => setEditingMember(null)}
                          autoFocus
                          className="appearance-none bg-white dark:bg-slate-950 border border-indigo-500/50 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-white pr-8 focus:outline-none"
                        >
                          {roles.map(r => (
                            <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                      </div>
                    ) : (
                      <button 
                        onClick={() => setEditingMember(member.id)}
                        className={`px-3 py-1 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-colors hover:bg-opacity-30 ${getRoleBadgeColor(member.role)}`}
                        title="Click to change role"
                      >
                        {member.role === 'owner' ? <ShieldAlert className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                        <ChevronDown className="w-3 h-3 ml-0.5 opacity-60" />
                      </button>
                    )}
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
                    {new Date(member.joined_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </td>
                  <td className="px-6 py-4 text-right">
                    {member.role !== 'owner' && (
                      <button
                        onClick={() => {
                          if (confirm('Are you sure you want to remove this member from the team?')) {
                            removeMember(activeTeam.id, member.user_id);
                          }
                        }}
                        className="p-2 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                        title="Remove Member"
                      >
                        <UserX className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {filteredMembers.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-slate-500 text-sm">
                    No members found matching your search query.
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
