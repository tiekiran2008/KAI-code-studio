import React, { Suspense, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { useUIStore } from '../../store/useUIStore';
import { useTeamStore } from '../../store/teamStore';
import { CommandPalette } from '../common/CommandPalette';
import { Sidebar } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import { AmbientCanvas } from '../ambient/AmbientCanvas';

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
  const initializeTeams = useTeamStore((state) => state.initializeTeams);

  useEffect(() => {
    initializeTeams();
  }, [initializeTeams]);

  return (
    <div className="min-h-screen flex bg-[#090d16] text-slate-100 app-layout-container transition-colors duration-300 relative">
      {/* Signature Ambient Focus Background Canvas */}
      <AmbientCanvas />

      <Sidebar />

      <div
        className={`flex-1 flex flex-col min-h-screen min-w-0 transition-all duration-300 relative z-10 ${
          sidebarCollapsed ? 'ml-20' : 'ml-64'
        }`}
      >
        <TopNavbar />

        <main className="flex-1 p-6 relative min-w-0 overflow-hidden flex flex-col">
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
