import { lazy } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { AuthLayout } from '../components/layout/AuthLayout';
import { ErrorBoundary } from '../components/common/ErrorBoundary';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';

// ---------------------------------------------------------------------------
// Route-level lazy imports — Phase 11.7B-1
// All page components use named exports, so we adapt them to default exports
// via the `.then(m => ({ default: m.Component }))` pattern.
// App shell (layouts, auth wrappers, error boundary) remain eagerly loaded.
// ---------------------------------------------------------------------------

// Core app pages
const DashboardPage = lazy(() =>
  import('../pages/DashboardPage').then(m => ({ default: m.DashboardPage }))
);
const RepositoryManagerPage = lazy(() =>
  import('../pages/RepositoryManagerPage').then(m => ({ default: m.RepositoryManagerPage }))
);
const WorkspacePage = lazy(() =>
  import('../pages/WorkspacePage').then(m => ({ default: m.WorkspacePage }))
);
const AgentMonitorPage = lazy(() =>
  import('../pages/AgentMonitorPage').then(m => ({ default: m.AgentMonitorPage }))
);
const MemoryCenterPage = lazy(() =>
  import('../pages/MemoryCenterPage').then(m => ({ default: m.MemoryCenterPage }))
);
const ToolActivityPage = lazy(() =>
  import('../pages/ToolActivityPage').then(m => ({ default: m.ToolActivityPage }))
);
const AnalyticsPage = lazy(() =>
  import('../pages/AnalyticsPage').then(m => ({ default: m.AnalyticsPage }))
);
const SettingsPage = lazy(() =>
  import('../pages/SettingsPage').then(m => ({ default: m.SettingsPage }))
);
const ProfilePage = lazy(() =>
  import('../pages/ProfilePage').then(m => ({ default: m.ProfilePage }))
);

// Workspace pages
const WorkspaceListPage = lazy(() =>
  import('../pages/workspaces/WorkspaceListPage').then(m => ({ default: m.WorkspaceListPage }))
);
const WorkspaceCreatePage = lazy(() =>
  import('../pages/workspaces/WorkspaceCreatePage').then(m => ({ default: m.WorkspaceCreatePage }))
);
const WorkspaceSettingsPage = lazy(() =>
  import('../pages/workspaces/WorkspaceSettingsPage').then(m => ({ default: m.WorkspaceSettingsPage }))
);

// Repository pages
const RepositoryImportWizard = lazy(() =>
  import('../pages/repositories/RepositoryImportWizard').then(m => ({ default: m.RepositoryImportWizard }))
);
const RepositoryDetails = lazy(() =>
  import('../pages/repositories/RepositoryDetails').then(m => ({ default: m.RepositoryDetails }))
);

// Project pages
const ProjectDashboard = lazy(() =>
  import('../pages/projects/ProjectDashboard').then(m => ({ default: m.ProjectDashboard }))
);
const ProjectDetails = lazy(() =>
  import('../pages/projects/ProjectDetails').then(m => ({ default: m.ProjectDetails }))
);

// Team pages
const TeamDashboard = lazy(() =>
  import('../pages/teams/TeamDashboard').then(m => ({ default: m.TeamDashboard }))
);
const TeamMembersPage = lazy(() =>
  import('../pages/teams/TeamMembersPage').then(m => ({ default: m.TeamMembersPage }))
);
const PendingInvitationsPage = lazy(() =>
  import('../pages/teams/PendingInvitationsPage').then(m => ({ default: m.PendingInvitationsPage }))
);
const RoleManagementPage = lazy(() =>
  import('../pages/teams/RoleManagementPage').then(m => ({ default: m.RoleManagementPage }))
);

// Review pages — these are the primary heavyweight routes
const CodeReviewPage = lazy(() =>
  import('../pages/reviews/CodeReviewPage').then(m => ({ default: m.CodeReviewPage }))
);
const ReviewHistoryPage = lazy(() =>
  import('../pages/reviews/ReviewHistoryPage').then(m => ({ default: m.ReviewHistoryPage }))
);
const ReviewResultsPage = lazy(() =>
  import('../pages/reviews/ReviewResultsPage').then(m => ({ default: m.ReviewResultsPage }))
);

// Reports page — pulls in chart/analytics heavy deps
const ReportsPage = lazy(() =>
  import('../pages/reports/ReportsPage').then(m => ({ default: m.ReportsPage }))
);

// Auth pages — lazy to keep initial parse cost minimal
// Auth state initialisation is in the Zustand store (eager), not in these page components,
// so lazy loading them does NOT delay authentication checks.
const LoginPage = lazy(() =>
  import('../pages/auth/LoginPage').then(m => ({ default: m.LoginPage }))
);
const SignupPage = lazy(() =>
  import('../pages/auth/SignupPage').then(m => ({ default: m.SignupPage }))
);
const ForgotPasswordPage = lazy(() =>
  import('../pages/auth/ForgotPasswordPage').then(m => ({ default: m.ForgotPasswordPage }))
);
const ResetPasswordPage = lazy(() =>
  import('../pages/auth/ResetPasswordPage').then(m => ({ default: m.ResetPasswordPage }))
);

// ---------------------------------------------------------------------------
// Router definition
// Suspense boundaries live in AppLayout and AuthLayout (see those files).
// The ErrorBoundary wrapping the root route catches any lazy-load failures
// and renders a recoverable error UI instead of a blank screen.
// ---------------------------------------------------------------------------

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    errorElement: <ErrorBoundary><div /></ErrorBoundary>,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'repositories', element: <RepositoryManagerPage /> },
      { path: 'repositories/import', element: <RepositoryImportWizard /> },
      { path: 'repositories/:repoId', element: <RepositoryDetails /> },
      { path: 'projects', element: <ProjectDashboard /> },
      { path: 'projects/:projectId', element: <ProjectDetails /> },
      { path: 'workspace', element: <WorkspacePage /> },
      { path: 'agents', element: <AgentMonitorPage /> },
      { path: 'memory', element: <MemoryCenterPage /> },
      { path: 'tools', element: <ToolActivityPage /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'workspaces', element: <WorkspaceListPage /> },
      { path: 'workspaces/new', element: <WorkspaceCreatePage /> },
      { path: 'workspaces/:workspaceId/settings', element: <WorkspaceSettingsPage /> },
      { path: 'teams', element: <TeamDashboard /> },
      { path: 'teams/members', element: <TeamMembersPage /> },
      { path: 'teams/invitations', element: <PendingInvitationsPage /> },
      { path: 'teams/roles', element: <RoleManagementPage /> },
      { path: 'reviews', element: <CodeReviewPage /> },
      { path: 'reviews/history', element: <ReviewHistoryPage /> },
      { path: 'reviews/:reviewId', element: <ReviewResultsPage /> },
      { path: 'reports', element: <ReportsPage /> },
    ],
  },
  {
    path: '/auth',
    element: <AuthLayout />,
    children: [
      { path: 'login', element: <LoginPage /> },
      { path: 'signup', element: <SignupPage /> },
      { path: 'forgot-password', element: <ForgotPasswordPage /> },
      { path: 'reset-password', element: <ResetPasswordPage /> },
    ],
  },
]);
