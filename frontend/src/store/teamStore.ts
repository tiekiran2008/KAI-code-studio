import { create } from 'zustand';
import { teamsApi, TeamCreateParams, TeamUpdateParams } from '../api/teams';
import { invitationsApi, InvitationCreateParams } from '../api/invitations';
import { Team, TeamMember, RoleEnum, Invitation, AuditLog, PermissionMatrixRow } from '../types';

interface TeamStoreState {
  teams: Team[];
  activeTeam: Team | null;
  teamInvitations: Invitation[];
  userInvitations: Invitation[];
  auditLogs: AuditLog[];
  permissionMatrix: PermissionMatrixRow[];
  isLoading: boolean;
  error: string | null;

  fetchTeams: () => Promise<void>;
  fetchTeam: (id: string) => Promise<Team>;
  createTeam: (data: TeamCreateParams) => Promise<Team>;
  updateTeam: (id: string, data: TeamUpdateParams) => Promise<Team>;
  deleteTeam: (id: string) => Promise<void>;
  transferOwnership: (id: string, newOwnerId: string) => Promise<Team>;
  changeMemberRole: (teamId: string, userId: string, role: RoleEnum) => Promise<TeamMember>;
  removeMember: (teamId: string, userId: string) => Promise<void>;
  leaveTeam: (teamId: string) => Promise<void>;
  
  fetchTeamInvitations: (teamId: string) => Promise<void>;
  fetchUserInvitations: () => Promise<void>;
  inviteMember: (teamId: string, data: InvitationCreateParams) => Promise<Invitation>;
  acceptInvitation: (token: string) => Promise<void>;
  rejectInvitation: (token: string) => Promise<void>;
  
  fetchAuditLogs: (teamId: string) => Promise<void>;
  fetchPermissionMatrix: () => Promise<void>;
  
  setActiveTeam: (team: Team | null) => void;
}

export const useTeamStore = create<TeamStoreState>((set, get) => ({
  teams: [],
  activeTeam: null,
  teamInvitations: [],
  userInvitations: [],
  auditLogs: [],
  permissionMatrix: [],
  isLoading: false,
  error: null,

  fetchTeams: async () => {
    set({ isLoading: true, error: null });
    try {
      const teams = await teamsApi.getTeams();
      set({ teams, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch teams', isLoading: false });
    }
  },

  fetchTeam: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const team = await teamsApi.getTeam(id);
      set({ activeTeam: team, isLoading: false });
      return team;
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch team', isLoading: false });
      throw err;
    }
  },

  createTeam: async (data: TeamCreateParams) => {
    set({ isLoading: true, error: null });
    try {
      const team = await teamsApi.createTeam(data);
      set((state) => ({
        teams: [...state.teams, team],
        activeTeam: team,
        isLoading: false,
      }));
      return team;
    } catch (err: any) {
      set({ error: err.message || 'Failed to create team', isLoading: false });
      throw err;
    }
  },

  updateTeam: async (id: string, data: TeamUpdateParams) => {
    try {
      const updated = await teamsApi.updateTeam(id, data);
      set((state) => ({
        teams: state.teams.map((t) => (t.id === id ? updated : t)),
        activeTeam: state.activeTeam?.id === id ? updated : state.activeTeam,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to update team' });
      throw err;
    }
  },

  deleteTeam: async (id: string) => {
    try {
      await teamsApi.deleteTeam(id);
      set((state) => ({
        teams: state.teams.filter((t) => t.id !== id),
        activeTeam: state.activeTeam?.id === id ? null : state.activeTeam,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete team' });
      throw err;
    }
  },

  transferOwnership: async (id: string, newOwnerId: string) => {
    try {
      const updated = await teamsApi.transferOwnership(id, newOwnerId);
      set((state) => ({
        teams: state.teams.map((t) => (t.id === id ? updated : t)),
        activeTeam: state.activeTeam?.id === id ? updated : state.activeTeam,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message || 'Failed to transfer ownership' });
      throw err;
    }
  },

  changeMemberRole: async (teamId: string, userId: string, role: RoleEnum) => {
    try {
      const updatedMember = await teamsApi.changeMemberRole(teamId, userId, role);
      set((state) => {
        if (!state.activeTeam || state.activeTeam.id !== teamId) return state;
        const members = state.activeTeam.members.map((m) =>
          m.user_id === userId ? { ...m, role: updatedMember.role } : m
        );
        const updatedTeam = { ...state.activeTeam, members };
        return {
          activeTeam: updatedTeam,
          teams: state.teams.map((t) => (t.id === teamId ? updatedTeam : t)),
        };
      });
      return updatedMember;
    } catch (err: any) {
      set({ error: err.message || 'Failed to change role' });
      throw err;
    }
  },

  removeMember: async (teamId: string, userId: string) => {
    try {
      await teamsApi.removeMember(teamId, userId);
      set((state) => {
        if (!state.activeTeam || state.activeTeam.id !== teamId) return state;
        const members = state.activeTeam.members.filter((m) => m.user_id !== userId);
        const updatedTeam = { ...state.activeTeam, members, member_count: members.length };
        return {
          activeTeam: updatedTeam,
          teams: state.teams.map((t) => (t.id === teamId ? updatedTeam : t)),
        };
      });
    } catch (err: any) {
      set({ error: err.message || 'Failed to remove member' });
      throw err;
    }
  },

  leaveTeam: async (teamId: string) => {
    try {
      await teamsApi.leaveTeam(teamId);
      set((state) => ({
        teams: state.teams.filter((t) => t.id !== teamId),
        activeTeam: state.activeTeam?.id === teamId ? null : state.activeTeam,
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to leave team' });
      throw err;
    }
  },

  fetchTeamInvitations: async (teamId: string) => {
    try {
      const invs = await invitationsApi.listTeamInvitations(teamId);
      set({ teamInvitations: invs });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch team invitations' });
    }
  },

  fetchUserInvitations: async () => {
    try {
      const invs = await invitationsApi.listUserInvitations();
      set({ userInvitations: invs });
    } catch (err: any) {
      set({ error: err.message || 'Failed to fetch user invitations' });
    }
  },

  inviteMember: async (teamId: string, data: InvitationCreateParams) => {
    try {
      const inv = await invitationsApi.inviteMember(teamId, data);
      set((state) => ({ teamInvitations: [...state.teamInvitations, inv] }));
      return inv;
    } catch (err: any) {
      set({ error: err.message || 'Failed to invite member' });
      throw err;
    }
  },

  acceptInvitation: async (token: string) => {
    try {
      await invitationsApi.acceptInvitation(token);
      set((state) => ({
        userInvitations: state.userInvitations.filter((i) => i.token !== token),
      }));
      await get().fetchTeams();
    } catch (err: any) {
      set({ error: err.message || 'Failed to accept invitation' });
      throw err;
    }
  },

  rejectInvitation: async (token: string) => {
    try {
      await invitationsApi.rejectInvitation(token);
      set((state) => ({
        userInvitations: state.userInvitations.filter((i) => i.token !== token),
      }));
    } catch (err: any) {
      set({ error: err.message || 'Failed to reject invitation' });
      throw err;
    }
  },

  fetchAuditLogs: async (teamId: string) => {
    try {
      const logs = await teamsApi.getAuditLogs(teamId);
      set({ auditLogs: logs });
    } catch (err: any) {
      console.error(err);
    }
  },

  fetchPermissionMatrix: async () => {
    try {
      const matrix = await teamsApi.getPermissionMatrix();
      set({ permissionMatrix: matrix });
    } catch (err: any) {
      console.error(err);
    }
  },

  setActiveTeam: (team: Team | null) => set({ activeTeam: team }),
}));
