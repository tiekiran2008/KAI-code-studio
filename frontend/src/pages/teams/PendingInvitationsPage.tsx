import React, { useEffect, useState } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { Mail, Clock, Shield, X, Search } from 'lucide-react';
import { InviteMemberModal } from './InviteMemberModal';

export const PendingInvitationsPage: React.FC = () => {
  const { activeTeam, teamInvitations, fetchTeamInvitations } = useTeamStore();
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (activeTeam) {
      fetchTeamInvitations(activeTeam.id);
    }
  }, [activeTeam, fetchTeamInvitations]);

  if (!activeTeam) {
    return <div className="text-gray-500 text-center p-8">No Active Team</div>;
  }

  const pendingInvites = teamInvitations.filter(i => i.status === 'pending');
  const filteredInvites = pendingInvites.filter(i => 
    i.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 backdrop-blur-sm">
        <div>
          <h1 className="text-2xl font-bold text-white mb-2">Pending Invitations</h1>
          <p className="text-gray-400">Manage sent invitations for {activeTeam.name}.</p>
        </div>
        <div className="flex gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search invitations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-gray-950/50 border border-gray-700/50 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500/50 w-64"
            />
          </div>
          <button 
            onClick={() => setIsInviteModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors"
          >
            <Mail className="w-4 h-4" />
            Invite Member
          </button>
        </div>
      </div>

      <div className="flex-1 bg-gray-900/40 rounded-2xl border border-gray-800/50 overflow-hidden flex flex-col">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-800/50 bg-gray-950/30">
                <th className="px-6 py-4 text-sm font-medium text-gray-400">Email Address</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-400">Role</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-400">Invited By</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-400">Sent On</th>
                <th className="px-6 py-4 text-sm font-medium text-gray-400 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {filteredInvites.map((invite) => (
                <tr key={invite.id} className="hover:bg-gray-800/20 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center shrink-0">
                        <Mail className="w-4 h-4 text-gray-400" />
                      </div>
                      <span className="text-sm font-medium text-white">{invite.email}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gray-800 text-gray-300 border border-gray-700">
                      <Shield className="w-3 h-3" />
                      {invite.role.charAt(0).toUpperCase() + invite.role.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-400">
                    {invite.invited_by}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-400">
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-gray-500" />
                      {new Date(invite.created_at).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      className="p-2 text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
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
                    <div className="flex flex-col items-center justify-center text-gray-500 gap-3">
                      <Mail className="w-10 h-10 text-gray-600" />
                      <p>No pending invitations found.</p>
                      <button 
                        onClick={() => setIsInviteModalOpen(true)}
                        className="text-indigo-400 hover:text-indigo-300 font-medium mt-2"
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
