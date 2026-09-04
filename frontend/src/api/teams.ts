import { fetchClient } from './fetchClient';
import { Team, TeamMember, RoleEnum, AuditLog, PermissionMatrixRow } from '../types';

export interface TeamCreateParams {
  name: string;
  description?: string;
}

export interface TeamUpdateParams {
  name?: string;
  description?: string;
}

export const teamsApi = {
  async getTeams(): Promise<Team[]> {
    return fetchClient.get<Team[]>('/teams');
  },

  async createTeam(data: TeamCreateParams): Promise<Team> {
    return fetchClient.post<Team>('/teams', data);
  },

  async getTeam(id: string): Promise<Team> {
    return fetchClient.get<Team>(`/teams/${id}`);
  },

  async updateTeam(id: string, data: TeamUpdateParams): Promise<Team> {
    return fetchClient.put<Team>(`/teams/${id}`, data);
  },

  async deleteTeam(id: string): Promise<void> {
    return fetchClient.delete(`/teams/${id}`);
  },

  async transferOwnership(id: string, newOwnerId: string): Promise<Team> {
    return fetchClient.post<Team>(`/teams/${id}/transfer-ownership`, { new_owner_user_id: newOwnerId });
  },

  async changeMemberRole(teamId: string, userId: string, role: RoleEnum): Promise<TeamMember> {
    return fetchClient.patch<TeamMember>(`/teams/${teamId}/members/${userId}/role`, { role });
  },

  async removeMember(teamId: string, userId: string): Promise<void> {
    return fetchClient.delete(`/teams/${teamId}/members/${userId}`);
  },

  async leaveTeam(teamId: string): Promise<void> {
    return fetchClient.post(`/teams/${teamId}/leave`);
  },

  async getAuditLogs(teamId: string, limit: number = 50): Promise<AuditLog[]> {
    return fetchClient.get<AuditLog[]>(`/teams/${teamId}/audit-logs`, { params: { limit } });
  },

  async getPermissionMatrix(): Promise<PermissionMatrixRow[]> {
    return fetchClient.get<PermissionMatrixRow[]>('/teams/rbac/permission-matrix');
  }
};
