import React, { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { Sparkles } from 'lucide-react';

/**
 * Minimal auth-route loading fallback — a small centered spinner shown
 * while the auth form chunk downloads. Same pure-CSS approach as AppLayout
 * to avoid pulling heavy libs into the initial bundle.
 */
const AuthRouteLoadingFallback: React.FC = () => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 120,
    }}
  >
    <div
      style={{
        width: 24,
        height: 24,
        borderRadius: '50%',
        border: '2px solid rgba(99,102,241,0.25)',
        borderTopColor: '#6366f1',
        animation: 'spin 0.7s linear infinite',
      }}
    />
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);

export const AuthLayout: React.FC = () => {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[#090d16] text-slate-100 relative overflow-hidden">
      {/* Decorative Background Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/20 rounded-full blur-[120px]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px]" />
      
      <div className="z-10 w-full max-w-md p-6">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-cyan-400 p-[2px] shadow-glow flex items-center justify-center mb-4">
            <div className="w-full h-full bg-[#090d16] rounded-[14px] flex items-center justify-center">
              <Sparkles className="w-7 h-7 text-indigo-400 animate-pulse" />
            </div>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
            Antigravity AI
          </h1>
          <p className="text-sm text-slate-400 text-center">
            Autonomous Engineering Platform
          </p>
        </div>

        <div className="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 p-8 rounded-2xl shadow-2xl">
          {/* Suspense boundary for lazy-loaded auth form chunks */}
          <Suspense fallback={<AuthRouteLoadingFallback />}>
            <Outlet />
          </Suspense>
        </div>
      </div>
    </div>
  );
};

