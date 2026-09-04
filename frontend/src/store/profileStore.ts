import { create } from 'zustand';
import { profileApi, UserProfile } from '../api/profile';

interface ProfileState {
  profile: UserProfile | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  
  fetchProfile: () => Promise<void>;
  updateProfile: (profileData: Partial<UserProfile>) => Promise<void>;
  clearError: () => void;
}

export const useProfileStore = create<ProfileState>((set) => ({
  profile: null,
  isLoading: false,
  isSaving: false,
  error: null,

  fetchProfile: async () => {
    set({ isLoading: true, error: null });
    try {
      const profile = await profileApi.getProfile();
      set({ profile, isLoading: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to fetch profile', isLoading: false });
    }
  },

  updateProfile: async (profileData) => {
    set({ isSaving: true, error: null });
    try {
      const updatedProfile = await profileApi.updateProfile(profileData);
      set({ profile: updatedProfile, isSaving: false });
    } catch (error: any) {
      set({ error: error.message || 'Failed to update profile', isSaving: false });
      throw error;
    }
  },

  clearError: () => set({ error: null })
}));
