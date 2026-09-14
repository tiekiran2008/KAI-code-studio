import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { TopNavbar } from './TopNavbar';
import { useAuthStore } from '../../store/authStore';
import { useProfileStore } from '../../store/profileStore';
import { ThemeProvider } from '../providers/ThemeProvider';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('TopNavbar User Menu & Logout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: { id: 'user-123', email: 'developer@kaistudio.dev', created_at: '2026-01-01' },
      accessToken: 'token-abc',
      refreshToken: 'refresh-abc',
      isAuthenticated: true,
      isLoading: false,
      error: null,
    });
    useProfileStore.setState({
      profile: {
        id: 'prof-123',
        user_id: 'user-123',
        name: 'Alex Developer',
        avatar: 'data:image/png;base64,mockAvatarData',
        bio: 'Fullstack Dev',
        timezone: 'UTC',
        theme_preference: 'dark',
        preferred_llm_provider: 'openai',
        default_ai_model: 'gpt-4o',
        notification_preferences: { email: true, in_app: true },
        created_at: '2026-01-01',
        updated_at: '2026-01-01',
      },
      avatarTimestamp: Date.now(),
      isLoading: false,
      isSaving: false,
      error: null,
    });
  });

  const renderNavbar = () => {
    return render(
      <MemoryRouter>
        <ThemeProvider>
          <TopNavbar />
        </ThemeProvider>
      </MemoryRouter>
    );
  };

  it('renders avatar image in user menu button when profile has avatar', () => {
    renderNavbar();
    const avatarImg = screen.getByAltText('Profile Avatar');
    expect(avatarImg).toBeInTheDocument();
    expect(avatarImg).toHaveAttribute('src', 'data:image/png;base64,mockAvatarData');
  });

  it('opens dropdown menu on click with user details and navigation links', () => {
    renderNavbar();
    const userMenuBtn = screen.getByRole('button', { name: /Open user menu/i });
    fireEvent.click(userMenuBtn);

    expect(screen.getByText('Alex Developer')).toBeInTheDocument();
    expect(screen.getByText('developer@kaistudio.dev')).toBeInTheDocument();
    expect(screen.getByText('Profile Settings')).toBeInTheDocument();
    expect(screen.getByText('Platform Settings')).toBeInTheDocument();
    expect(screen.getByText('Log Out')).toBeInTheDocument();
  });

  it('triggers logout, resets session, and navigates to /auth/login on Log Out click', async () => {
    const mockLogout = vi.fn().mockResolvedValue(undefined);
    useAuthStore.setState({ logout: mockLogout });
    renderNavbar();

    const userMenuBtn = screen.getByRole('button', { name: /Open user menu/i });
    fireEvent.click(userMenuBtn);

    const logoutBtn = screen.getByRole('button', { name: /Log Out/i });
    fireEvent.click(logoutBtn);

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith('/auth/login');
    });

    expect(useProfileStore.getState().profile).toBeNull();
  });
});
