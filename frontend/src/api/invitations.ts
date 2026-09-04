import { fetchClient } from './fetchClient';
import { Invitation, RoleEnum } from '../types';

export interface InvitationCreateParams {
  email: string;
  role: RoleEnum;
}

export const invitationsApi = {
  async inviteMember(teamId: string, data: InvitationCreateParams): Promise<Invitation> {
    return fetchClient.post<Invitation>(`/teams/${teamId}/invitations`, data);
  },

  async listTeamInvitations(teamId: string): Promise<Invitation[]> {
    return fetchClient.get<Invitation[]>(`/teams/${teamId}/invitations`);
  },

  async listUserInvitations(): Promise<Invitation[]> {
    return fetchClient.get<Invitation[]>('/invitations');
  },

  async acceptInvitation(token: string): Promise<void> {
    return fetchClient.post(`/invitations/${token}/accept`);
  },

  async rejectInvitation(token: string): Promise<void> {
    return fetchClient.post(`/invitations/${token}/reject`);
  }
};
