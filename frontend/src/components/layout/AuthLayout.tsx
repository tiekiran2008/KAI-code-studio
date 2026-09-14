import React, { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import kaiLogo from '../../assets/branding/kai-logo.png';

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
    <div className="min-h-screen w-full flex items-center justify-center bg-[#090d16] text-slate-100 relative overflow-hidden py-10 px-4 sm:px-6">
      {/* Decorative Background Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] pointer-events-none" />
      
      <div className="z-10 w-full max-w-md">
        <div className="flex flex-col items-center mb-6 text-center">
          <div className="relative mb-3 group">
            <div className="absolute -inset-1.5 rounded-full bg-gradient-to-r from-cyan-500/30 via-indigo-500/30 to-purple-500/30 blur-md opacity-75 group-hover:opacity-100 transition duration-500 pointer-events-none" />
            <img
              src={kaiLogo}
              alt="KAI Code Studio Logo"
              className="relative w-20 h-20 sm:w-24 sm:h-24 object-contain drop-shadow-[0_0_20px_rgba(99,102,241,0.45)] transition-transform duration-300 hover:scale-105"
            />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-2 leading-tight">
            Welcome to KAI<br />
            <span className="bg-gradient-to-r from-cyan-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
              Code Studio
            </span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed max-w-xs">
            Your Intelligent AI Assistant powered by<br />
            <span className="text-slate-300 font-medium">Kiran Artificial Intelligence</span>
          </p>
        </div>

        <div className="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 p-6 sm:p-8 rounded-2xl shadow-2xl">
          {/* Suspense boundary for lazy-loaded auth form chunks */}
          <Suspense fallback={<AuthRouteLoadingFallback />}>
            <Outlet />
          </Suspense>
        </div>
      </div>
    </div>
  );
};

