import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';
import { useAuthStore } from '../../store/authStore';

vi.mock('../../store/authStore', () => ({
  useAuthStore: vi.fn(),
}));

describe('LoginPage Component', () => {
  const mockLogin = vi.fn();
  const mockLoginWithOAuth = vi.fn();
  const mockClearError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useAuthStore as any).mockReturnValue({
      login: mockLogin,
      loginWithOAuth: mockLoginWithOAuth,
      isLoading: false,
      error: null,
      clearError: mockClearError,
    });
  });

  it('renders login form and OAuth buttons', () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Continue with Google/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Continue with GitHub/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('you@example.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
  });

  it('triggers loginWithOAuth when Google button is clicked', async () => {
    mockLoginWithOAuth.mockResolvedValueOnce(undefined);

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    const googleBtn = screen.getByRole('button', { name: /Continue with Google/i });
    fireEvent.click(googleBtn);

    expect(mockClearError).toHaveBeenCalled();
    expect(mockLoginWithOAuth).toHaveBeenCalledWith('google');
  });

  it('triggers loginWithOAuth when GitHub button is clicked', async () => {
    mockLoginWithOAuth.mockResolvedValueOnce(undefined);

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    const githubBtn = screen.getByRole('button', { name: /Continue with GitHub/i });
    fireEvent.click(githubBtn);

    expect(mockClearError).toHaveBeenCalled();
    expect(mockLoginWithOAuth).toHaveBeenCalledWith('github');
  });

  it('handles email/password submission', async () => {
    mockLogin.mockResolvedValueOnce(undefined);

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    fireEvent.change(screen.getByPlaceholderText('you@example.com'), {
      target: { value: 'user@example.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('••••••••'), {
      target: { value: 'password123' },
    });

    const signInBtn = screen.getByRole('button', { name: /Sign In/i });
    fireEvent.click(signInBtn);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('user@example.com', 'password123');
    });
  });

  it('displays error message when auth error exists', () => {
    (useAuthStore as any).mockReturnValue({
      login: mockLogin,
      loginWithOAuth: mockLoginWithOAuth,
      isLoading: false,
      error: 'Invalid credentials provided',
      clearError: mockClearError,
    });

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    expect(screen.getByText('Invalid credentials provided')).toBeInTheDocument();
  });
});
