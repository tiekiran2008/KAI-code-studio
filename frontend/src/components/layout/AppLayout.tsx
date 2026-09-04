import React, { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { useUIStore } from '../../store/useUIStore';
import { CommandPalette } from '../common/CommandPalette';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';

/**
 * Lightweight pure-CSS route loading fallback.
 * Intentionally avoids framer-motion and other heavy libs so this
 * component does not add to the initial bundle.
 */
const RouteLoadingFallback: React.FC = () => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100%',
      flex: 1,
    }}
  >
    <div
      style={{
        width: 32,
        height: 32,
        borderRadius: '50%',
        border: '2px solid rgba(99,102,241,0.25)',
        borderTopColor: '#6366f1',
        animation: 'spin 0.7s linear infinite',
      }}
    />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

export const AppLayout: React.FC = () => {
  const { sidebarCollapsed } = useUIStore();

  return (
    <div className="min-h-screen flex bg-[#090d16] text-slate-100 transition-colors duration-300">
      <Sidebar />

      <div
        className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${
          sidebarCollapsed ? 'ml-20' : 'ml-64'
        }`}
      >
        <TopNavbar />

        <main className="flex-1 p-6 relative">
          {/* Single Suspense boundary for all route-level lazy chunks */}
          <Suspense fallback={<RouteLoadingFallback />}>
            <Outlet />
          </Suspense>
        </main>
      </div>

      {/* Global Overlays */}
      <CommandPalette />
    </div>
  );
};
