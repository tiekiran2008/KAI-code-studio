import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
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
      isRemovingAvatar: false,
      error: null,
    });
  });

  it('renders profile settings form with current user avatar and Remove photo button', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(sampleProfile);
    await act(async () => {
      render(<ProfilePage />);
    });

    expect(screen.getByText('Profile Settings')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Jane Doe')).toBeInTheDocument();
    const img = screen.getByAltText('Avatar');
    expect(img).toHaveAttribute('src', 'https://example.com/avatar-initial.png');
    expect(screen.getByRole('button', { name: 'Remove photo' })).toBeInTheDocument();
  });

  it('submits updated profile photo and refreshes store immediately', async () => {
    const updatedProfile: UserProfile = {
      ...sampleProfile,
      avatar: 'data:image/png;base64,newUploadedPhoto',
    };
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(sampleProfile);
    vi.spyOn(profileApi, 'updateProfile').mockResolvedValue(updatedProfile);

    await act(async () => {
      render(<ProfilePage />);
    });

    const saveBtn = screen.getByRole('button', { name: /Save Changes/i });
    await act(async () => {
      fireEvent.click(saveBtn);
    });

    await waitFor(() => {
      expect(profileApi.updateProfile).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Profile saved successfully')).toBeInTheDocument();
    });
  });

  it('displays error banner when profile update fails', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(sampleProfile);
    vi.spyOn(profileApi, 'updateProfile').mockRejectedValue(new Error('Network error uploading avatar'));

    await act(async () => {
      render(<ProfilePage />);
    });

    const saveBtn = screen.getByRole('button', { name: /Save Changes/i });
    await act(async () => {
      fireEvent.click(saveBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('Network error uploading avatar')).toBeInTheDocument();
    });
  });

  it('opens confirmation modal when clicking Remove photo, and closes without removing when clicking Cancel', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(sampleProfile);
    vi.spyOn(profileApi, 'removeAvatar');

    await act(async () => {
      render(<ProfilePage />);
    });

    const removeBtn = screen.getByRole('button', { name: 'Remove photo' });
    await act(async () => {
      fireEvent.click(removeBtn);
    });

    // Confirmation modal should be visible
    expect(screen.getByRole('heading', { name: 'Remove Profile Photo' })).toBeInTheDocument();
    expect(
      screen.getByText(/Are you sure you want to remove your profile photo\?/i)
    ).toBeInTheDocument();

    // Click cancel inside the modal dialog
    const modal = screen.getByRole('dialog');
    const cancelModalBtn = modal.querySelector('button:not(#btn-confirm-remove-photo)') as HTMLButtonElement;
    await act(async () => {
      fireEvent.click(cancelModalBtn);
    });

    expect(screen.queryByRole('heading', { name: 'Remove Profile Photo' })).not.toBeInTheDocument();
    expect(profileApi.removeAvatar).not.toHaveBeenCalled();
    // Avatar image should still be rendered
    expect(screen.getByAltText('Avatar')).toBeInTheDocument();
  });

  it('removes profile photo on confirmation, falls back to default avatar, and displays success', async () => {
    const profileWithoutAvatar: UserProfile = {
      ...sampleProfile,
      avatar: null,
    };
    vi.spyOn(profileApi, 'getProfile')
      .mockResolvedValueOnce(sampleProfile)
      .mockResolvedValue(profileWithoutAvatar);
    vi.spyOn(profileApi, 'removeAvatar').mockResolvedValue(profileWithoutAvatar);

    await act(async () => {
      render(<ProfilePage />);
    });

    const removeBtn = screen.getByRole('button', { name: 'Remove photo' });
    await act(async () => {
      fireEvent.click(removeBtn);
    });

    const modal = screen.getByRole('dialog');
    const confirmBtn = modal.querySelector('#btn-confirm-remove-photo') as HTMLButtonElement;
    await act(async () => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(profileApi.removeAvatar).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Profile photo removed successfully')).toBeInTheDocument();
    });

    // Avatar image element should no longer be present
    expect(screen.queryByAltText('Avatar')).not.toBeInTheDocument();
    // Remove photo button should no longer be present
    expect(screen.queryByRole('button', { name: 'Remove photo' })).not.toBeInTheDocument();
  });

  it('handles error gracefully when remove photo API fails', async () => {
    vi.spyOn(profileApi, 'getProfile').mockResolvedValue(sampleProfile);
    vi.spyOn(profileApi, 'removeAvatar').mockRejectedValue(new Error('Failed to delete avatar on server'));
    vi.spyOn(profileApi, 'updateProfile').mockRejectedValue(new Error('Failed to delete avatar on server'));

    await act(async () => {
      render(<ProfilePage />);
    });

    const removeBtn = screen.getByRole('button', { name: 'Remove photo' });
    await act(async () => {
      fireEvent.click(removeBtn);
    });

    const modal = screen.getByRole('dialog');
    const confirmBtn = modal.querySelector('#btn-confirm-remove-photo') as HTMLButtonElement;
    await act(async () => {
      fireEvent.click(confirmBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('Failed to delete avatar on server')).toBeInTheDocument();
    });

    // Modal stays open showing the error so user can retry or cancel
    expect(screen.getByRole('heading', { name: 'Remove Profile Photo' })).toBeInTheDocument();
  });
});
