import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProfilePage } from './ProfilePage';
import { useProfileStore } from '../store/profileStore';
import { profileApi, UserProfile } from '../api/profile';

describe('ProfilePage and Photo Update', () => {
  const sampleProfile: UserProfile = {
    id: 'prof-100',
    user_id: 'user-100',
    name: 'Jane Doe',
    avatar: 'https://example.com/avatar-initial.png',
    bio: 'Software Engineer',
    timezone: 'UTC',
    theme_preference: 'dark',
    preferred_llm_provider: 'openai',
    default_ai_model: 'gpt-4o',
    notification_preferences: { email: true, in_app: true },
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    useProfileStore.setState({
      profile: sampleProfile,
      avatarTimestamp: Date.now(),
      isLoading: false,
      isSaving: false,
      error: null,
    });
  });

  it('renders profile settings form with current user avatar', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValueOnce(sampleProfile);
    render(<ProfilePage />);

    expect(screen.getByText('Profile Settings')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Jane Doe')).toBeInTheDocument();
    const img = screen.getByAltText('Avatar');
    expect(img).toHaveAttribute('src', 'https://example.com/avatar-initial.png');
  });

  it('submits updated profile photo and refreshes store immediately', async () => {
    const updatedProfile: UserProfile = {
      ...sampleProfile,
      avatar: 'data:image/png;base64,newUploadedPhoto',
    };
    vi.spyOn(profileApi, 'getProfile').mockResolvedValueOnce(sampleProfile);
    vi.spyOn(profileApi, 'updateProfile').mockResolvedValueOnce(updatedProfile);

    render(<ProfilePage />);

    const saveBtn = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(profileApi.updateProfile).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Profile saved successfully')).toBeInTheDocument();
    });
  });

  it('displays error banner when profile update fails', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValueOnce(sampleProfile);
    vi.spyOn(profileApi, 'updateProfile').mockRejectedValueOnce(new Error('Network error uploading avatar'));

    render(<ProfilePage />);

    const saveBtn = screen.getByRole('button', { name: /Save Changes/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText('Network error uploading avatar')).toBeInTheDocument();
    });
  });
});
