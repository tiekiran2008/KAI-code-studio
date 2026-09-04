const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_PREFIX = import.meta.env.VITE_API_PREFIX || '/api/v1';

const BASE_URL = `${API_BASE_URL}${API_PREFIX}/auth`;

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
    const response = await fetch(`${BASE_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  },

  async signup(email: string, password: string): Promise<UserSession> {
    const response = await fetch(`${BASE_URL}/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Signup failed');
    }

    return response.json();
  },

  async logout(token: string): Promise<void> {
    const response = await fetch(`${BASE_URL}/logout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      console.error('Logout request failed');
    }
  },

  async refreshToken(refreshToken: string): Promise<UserSession> {
    const response = await fetch(`${BASE_URL}/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Token refresh failed');
    }

    return response.json();
  },

  async getCurrentUser(token: string): Promise<{ user: any }> {
    const response = await fetch(`${BASE_URL}/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch user');
    }

    return response.json();
  }
};
