import { fetchClient } from './fetchClient';

export interface NotificationPreferences {
  email: boolean;
  in_app: boolean;
}

export interface UserProfile {
  id: string;
  user_id: string;
  name: string | null;
  avatar: string | null;
  bio: string | null;
  timezone: string;
  theme_preference: string;
  preferred_llm_provider: string;
  default_ai_model: string;
  notification_preferences: NotificationPreferences;
  created_at: string | null;
  updated_at: string | null;
}

export const profileApi = {
  async getProfile(): Promise<UserProfile> {
    return fetchClient.get<UserProfile>('/profile');
  },

  async updateProfile(profileData: Partial<UserProfile>): Promise<UserProfile> {
    return fetchClient.put<UserProfile>('/profile', profileData);
  },

  async removeAvatar(): Promise<UserProfile> {
    return fetchClient.delete<UserProfile>('/profile/avatar');
  }
};

