import { fetchClient, buildApiUrl } from './fetchClient';

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface UserSession {
  access_token?: string | null;
  refresh_token?: string | null;
  expires_in?: number | null;
  user: User;
  message?: string | null;
  confirmation_required?: boolean;
}

export const authApi = {
  async login(email: string, password: string): Promise<UserSession> {
    return fetchClient.post<UserSession>('/auth/login', { email, password });
  },

  async signup(email: string, password: string): Promise<UserSession> {
    return fetchClient.post<UserSession>('/auth/signup', { email, password });
  },

  async logout(token: string): Promise<void> {
    try {
      await fetch(buildApiUrl('/auth/logout'), {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
    } catch (e) {
      console.error('Logout request failed', e);
    }
  },

  async refreshToken(refreshToken: string): Promise<UserSession> {
    return fetchClient.post<UserSession>('/auth/refresh', { refresh_token: refreshToken });
  },

  async getCurrentUser(token: string): Promise<{ user: any }> {
    const res = await fetch(buildApiUrl('/auth/me'), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to fetch user');
    }

    return res.json();
  }
};

