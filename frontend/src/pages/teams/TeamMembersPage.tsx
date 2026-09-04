import React, { useState } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { Search, ShieldAlert, UserX, User, Shield, ChevronDown } from 'lucide-react';
import { RoleEnum } from '../../types';

export const TeamMembersPage: React.FC = () => {
  const { activeTeam, changeMemberRole, removeMember } = useTeamStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [editingMember, setEditingMember] = useState<string | null>(null);

  if (!activeTeam) {
    return <div className="text-gray-500 text-center p-8">No Active Team</div>;
  }

  const filteredMembers = activeTeam.members.filter(m => 
    m.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
    m.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.user_id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const roles: RoleEnum[] = ['owner', 'admin', 'maintainer', 'developer', 'reviewer', 'viewer'];

  const getRoleBadgeColor = (role: RoleEnum) => {
    switch (role) {
      case 'owner': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'admin': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'maintainer': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'developer': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'reviewer': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      case 'viewer': return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
      default: return 'bg-gray-500/10 text-gray-400 border-gray-500/20';
    }
  };

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 backdrop-blur-sm">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Team Members</h1>
          <p className="text-gray-400">Manage members and their roles in {activeTeam.name}.</p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search members..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-4 py-2 bg-gray-950/50 border border-gray-700/50 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500/50 w-64"
          />
        </div>
      </div>

      <div className="flex-1 bg-gray-900/40 rounded-2xl border border-gray-800/50 overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-800/50 bg-gray-950/30">
                <th className="px-6 py-4 text-sm font-medium text-gray-400">Member</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-400">Role</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-400">Joined</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-400 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {filteredMembers.map((member) => (
                <tr key={member.id} className="hover:bg-gray-800/20 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/20 flex items-center justify-center shrink-0">
                        {member.avatar ? (
                          <img src={member.avatar} alt={member.name} className="w-full h-full rounded-full object-cover" />
                        ) : (
                          <User className="w-5 h-5 text-indigo-400" />
                        )}
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">{member.name || member.email || member.user_id}</div>
                        <div className="text-xs text-gray-500">{member.email || member.user_id}</div>
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
                          className="appearance-none bg-gray-950/50 border border-indigo-500/50 rounded-lg px-3 py-1.5 text-sm text-white pr-8 focus:outline-none"
                        >
                          {roles.map(r => (
                            <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                          ))}
                        </select>
                        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                      </div>
                    ) : (
                      <button 
                        onClick={() => setEditingMember(member.id)}
                        className={`px-3 py-1 rounded-full text-xs font-medium border flex items-center gap-1.5 transition-colors hover:bg-opacity-20 ${getRoleBadgeColor(member.role)}`}
                      >
                        {member.role === 'owner' ? <ShieldAlert className="w-3 h-3" /> : <Shield className="w-3 h-3" />}
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                      </button>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-400">
                    {new Date(member.joined_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => {
                        if (confirm('Are you sure you want to remove this member?')) {
                          removeMember(activeTeam.id, member.user_id);
                        }
                      }}
                      className="p-2 text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                      title="Remove Member"
                    >
                      <UserX className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {filteredMembers.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                    No members found matching your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
