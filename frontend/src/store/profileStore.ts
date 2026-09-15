import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { profileApi, UserProfile } from '../api/profile';

interface ProfileState {
  profile: UserProfile | null;
  avatarTimestamp: number;
  isLoading: boolean;
  isSaving: boolean;
  isRemovingAvatar: boolean;
  error: string | null;
  
  fetchProfile: () => Promise<void>;
  updateProfile: (profileData: Partial<UserProfile>) => Promise<UserProfile>;
  removeAvatar: () => Promise<UserProfile>;
  setProfile: (profile: UserProfile | null) => void;
  clearError: () => void;
}

export const useProfileStore = create<ProfileState>()(
  persist(
    (set) => ({
      profile: null,
      avatarTimestamp: Date.now(),
      isLoading: false,
      isSaving: false,
      isRemovingAvatar: false,
      error: null,

      fetchProfile: async () => {
        set({ isLoading: true, error: null });
        try {
          const profile = await profileApi.getProfile();
          set({ profile, isLoading: false, avatarTimestamp: Date.now() });
        } catch (error: any) {
          set({ error: error.message || 'Failed to fetch profile', isLoading: false });
        }
      },

      updateProfile: async (profileData) => {
        set({ isSaving: true, error: null });
        try {
          const updatedProfile = await profileApi.updateProfile(profileData);
          set({ profile: updatedProfile, isSaving: false, avatarTimestamp: Date.now() });
          return updatedProfile;
        } catch (error: any) {
          set({ error: error.message || 'Failed to update profile', isSaving: false });
          throw error;
        }
      },

      removeAvatar: async () => {
        set({ isRemovingAvatar: true, error: null });
        try {
          // Attempt DELETE /profile/avatar, falling back to PUT /profile with { avatar: null }
          let updatedProfile: UserProfile;
          try {
            updatedProfile = await profileApi.removeAvatar();
          } catch {
            updatedProfile = await profileApi.updateProfile({ avatar: null });
          }
          set({ profile: updatedProfile, isRemovingAvatar: false, avatarTimestamp: Date.now() });
          return updatedProfile;
        } catch (error: any) {
          set({ error: error.message || 'Failed to remove profile photo', isRemovingAvatar: false });
          throw error;
        }
      },

      setProfile: (profile) => set({ profile, avatarTimestamp: Date.now() }),

      clearError: () => set({ error: null })
    }),
    {
      name: 'user-profile-storage',
      partialize: (state) => ({ profile: state.profile, avatarTimestamp: state.avatarTimestamp }),
    }
  )
);


