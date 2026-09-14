import React, { useState, useRef, useEffect } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { useUIStore } from '../../store/useUIStore';
import { useSettingsStore } from '../../store/useSettingsStore';
import { useAuthStore } from '../../store/authStore';
import { useProfileStore } from '../../store/profileStore';
import { useTheme } from '../providers/ThemeProvider';
import { Search, Activity, Sun, Moon, Sparkles, UserCircle, User, Settings, LogOut, ChevronDown, Check } from 'lucide-react';
import { navItems } from './Sidebar';
import { WorkspaceSwitcher } from '../workspace/WorkspaceSwitcher';
import { FocusSessionIndicator } from '../ambient/FocusSessionIndicator';

export const TopNavbar: React.FC = () => {
  const { setCommandPaletteOpen } = useUIStore();
  const { llm } = useSettingsStore();
  const { user, isAuthenticated, logout } = useAuthStore();
  const { profile, fetchProfile, setProfile } = useProfileStore();
  const { theme, setTheme, resolvedTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();

  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const themeMenuRef = useRef<HTMLDivElement>(null);

  const currentNav = navItems.find((n) => n.path === location.pathname) || navItems[0];

  useEffect(() => {
    if (isAuthenticated && !profile) {
      fetchProfile().catch(() => {});
    }
  }, [isAuthenticated, profile, fetchProfile]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (themeMenuRef.current && !themeMenuRef.current.contains(event.target as Node)) {
        setIsThemeMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdown on route change
  useEffect(() => {
    setIsUserMenuOpen(false);
    setIsThemeMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    setIsUserMenuOpen(false);
    await logout();
    setProfile(null);
    navigate('/auth/login');
  };

  const displayName = profile?.name || user?.email?.split('@')[0] || 'User';
  const displayEmail = user?.email || 'user@kaistudio.dev';

  return (
    <header className="h-16 px-6 bg-[#0f172a]/60 backdrop-blur-md border-b border-slate-800/80 sticky top-0 z-30 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-semibold text-white tracking-tight flex items-center gap-2">
          {currentNav.name}
        </h1>
        <div className="hidden md:block h-5 w-px bg-slate-700/60 mx-1" />
        <div className="hidden md:block">
          <WorkspaceSwitcher />
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Focus Session Active Pill */}
        <FocusSessionIndicator />

        {/* Command Palette Trigger */}
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 text-xs transition-colors"
        >
          <Search className="w-3.5 h-3.5 text-indigo-400" />
          <span>Search platform...</span>
          <kbd className="bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded text-[10px] font-mono border border-slate-700">
            Cmd+K
          </kbd>
        </button>

        {/* Model Selector Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs font-mono">
          <Activity className="w-3.5 h-3.5 text-indigo-400 animate-pulse" />
          <span>{llm?.modelName || 'GPT-4o'}</span>
        </div>

        {/* Theme Selector Dropdown */}
        <div className="relative" ref={themeMenuRef}>
          <button
            id="btn-theme-menu"
            onClick={() => setIsThemeMenuOpen((prev) => !prev)}
            className={`p-2 rounded-xl border transition-all flex items-center gap-1.5 ${
              resolvedTheme === 'ambient'
                ? 'bg-indigo-950/60 border-indigo-500/50 text-indigo-300 shadow-glow'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
            }`}
            aria-label="Select theme"
            title="Theme Selection"
          >
            {resolvedTheme === 'ambient' ? (
              <Sparkles className="w-4 h-4 text-cyan-400" />
            ) : resolvedTheme === 'light' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-400" />
            )}
            <ChevronDown className="w-3 h-3 opacity-60" />
          </button>

          {isThemeMenuOpen && (
            <div
              id="theme-dropdown-menu"
              className="absolute right-0 mt-2 w-56 rounded-2xl bg-slate-900/95 backdrop-blur-xl border border-slate-800 shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150"
            >
              <div className="px-3 py-1.5 text-[11px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-800/80 mb-1">
                Appearance & Theme
              </div>

              <button
                type="button"
                onClick={() => {
                  setTheme('dark');
                  setIsThemeMenuOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-colors ${
                  theme === 'dark'
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Moon className="w-4 h-4 text-indigo-400" />
                  <span>Dark Glass (Default)</span>
                </div>
                {theme === 'dark' && <Check className="w-3.5 h-3.5 text-indigo-400" />}
              </button>

              <button
                type="button"
                onClick={() => {
                  setTheme('light');
                  setIsThemeMenuOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-colors mt-1 ${
                  theme === 'light'
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Sun className="w-4 h-4 text-amber-400" />
                  <span>Light Mode</span>
                </div>
                {theme === 'light' && <Check className="w-3.5 h-3.5 text-indigo-400" />}
              </button>

              <button
                type="button"
                onClick={() => {
                  setTheme('ambient');
                  setIsThemeMenuOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all mt-1 ${
                  theme === 'ambient'
                    ? 'bg-gradient-to-r from-indigo-900/60 to-purple-900/60 text-cyan-300 border border-cyan-500/40 shadow-glow'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Sparkles className="w-4 h-4 text-cyan-400" />
                  <div className="flex flex-col text-left">
                    <span>Ambient Focus</span>
                    <span className="text-[10px] text-cyan-400/80 font-normal">Signature Experience</span>
                  </div>
                </div>
                {theme === 'ambient' && <Check className="w-3.5 h-3.5 text-cyan-400" />}
              </button>
            </div>
          )}
        </div>

        {/* User / Profile Menu Dropdown */}
        <div className="relative" ref={menuRef}>
          <button
            id="btn-user-menu"
            onClick={() => setIsUserMenuOpen((prev) => !prev)}
            className={`flex items-center gap-2 p-1.5 rounded-xl border transition-all ${
              isUserMenuOpen || location.pathname === '/profile'
                ? 'bg-indigo-900/30 border-indigo-500/50 text-indigo-300 shadow-glow'
                : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white hover:border-slate-700'
            }`}
            aria-expanded={isUserMenuOpen}
            aria-label="Open user menu"
          >
            {profile?.avatar ? (
              <img
                src={profile.avatar}
                alt="Profile Avatar"
                className="w-6 h-6 rounded-full object-cover border border-indigo-500/40"
              />
            ) : (
              <UserCircle className="w-5 h-5 text-indigo-400" />
            )}
            <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isUserMenuOpen ? 'rotate-180 text-indigo-400' : 'text-slate-500'}`} />
          </button>

          {isUserMenuOpen && (
            <div
              id="user-dropdown-menu"
              className="absolute right-0 mt-2 w-64 rounded-2xl bg-slate-900/95 backdrop-blur-xl border border-slate-800 shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150"
            >
              {/* User Details Header */}
              <div className="px-3 py-2.5 border-b border-slate-800/80 mb-1 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full overflow-hidden bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                  {profile?.avatar ? (
                    <img src={profile.avatar} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                    <User className="w-5 h-5 text-indigo-400" />
                  )}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-semibold text-white truncate">{displayName}</span>
                  <span className="text-[11px] text-slate-400 truncate">{displayEmail}</span>
                </div>
              </div>

              {/* Navigation Actions */}
              <div className="space-y-0.5">
                <Link
                  to="/profile"
                  onClick={() => setIsUserMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors"
                >
                  <User className="w-4 h-4 text-indigo-400" />
                  <span>Profile Settings</span>
                </Link>
                <Link
                  to="/settings"
                  onClick={() => setIsUserMenuOpen(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 transition-colors"
                >
                  <Settings className="w-4 h-4 text-slate-400" />
                  <span>Platform Settings</span>
                </Link>
              </div>

              <div className="h-px bg-slate-800/80 my-1" />

              {/* Logout Option */}
              <button
                id="btn-logout"
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-rose-400 hover:text-rose-200 hover:bg-rose-500/10 transition-colors text-left"
              >
                <LogOut className="w-4 h-4 text-rose-400" />
                <span>Log Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
