import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useTeamStore } from '../../store/teamStore';
import {
  Users,
  Shield,
  Mail,
  Settings,
  LayoutDashboard,
  ChevronDown,
  Plus,
  UserPlus,
  Check,
  Building2,
  Sparkles
} from 'lucide-react';
import { CreateTeamModal } from './CreateTeamModal';
import { InviteMemberModal } from './InviteMemberModal';

export const TeamHeaderNav: React.FC = () => {
  const { teams, activeTeam, setActiveTeam } = useTeamStore();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navTabs = [
    { name: 'Overview', path: '/teams', icon: LayoutDashboard, exact: true },
    { name: 'Members', path: '/teams/members', icon: Users },
    { name: 'Invitations', path: '/teams/invitations', icon: Mail },
    { name: 'Roles & Permissions', path: '/teams/roles', icon: Shield },
    { name: 'Settings', path: '/teams/settings', icon: Settings },
  ];

  return (
    <div className="flex flex-col gap-4 mb-2">
      {/* Top Banner & Team Switcher Bar */}
      <div className="glass-panel flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl shadow-lg shadow-black/5 dark:shadow-black/20">
        
        {/* Left: Team Selector */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-3 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200/80 border border-slate-300/80 dark:bg-slate-900/80 dark:hover:bg-slate-800/80 dark:border-slate-700/60 text-left transition-all duration-200 group"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center shrink-0 shadow-md shadow-indigo-500/20">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <div className="min-w-0 pr-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-900 dark:text-white truncate max-w-[160px] md:max-w-[220px]">
                  {activeTeam ? activeTeam.name : 'Select a Team'}
                </span>
                {activeTeam && (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-500/30">
                    {activeTeam.member_count} member{activeTeam.member_count !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                {teams.length} team{teams.length !== 1 ? 's' : ''} available
              </p>
            </div>
            <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180 text-slate-800 dark:text-white' : 'group-hover:text-slate-800 dark:group-hover:text-white'}`} />
          </button>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute left-0 top-full mt-2 w-72 rounded-2xl glass-panel bg-white dark:bg-[#0b0f19] border border-slate-200 dark:border-slate-800 shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3 py-2 text-[11px] font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Switch Team
              </div>
              
              <div className="max-h-60 overflow-y-auto space-y-1 custom-scrollbar">
                {teams.length === 0 ? (
                  <div className="px-3 py-4 text-xs text-center text-slate-500">
                    No teams found
                  </div>
                ) : (
                  teams.map((t) => {
                    const isCurrent = activeTeam?.id === t.id;
                    return (
                      <button
                        key={t.id}
                        onClick={() => {
                          setActiveTeam(t);
                          setIsDropdownOpen(false);
                        }}
                        className={`w-full flex items-center justify-between p-2.5 rounded-xl text-left text-sm transition-colors ${
                          isCurrent
                            ? 'bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/30'
                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-white'
                        }`}
                      >
                        <div className="min-w-0 pr-2">
                          <p className="font-medium truncate">{t.name}</p>
                          <p className="text-xs text-slate-500 truncate">
                            {t.member_count} member{t.member_count !== 1 ? 's' : ''}
                          </p>
                        </div>
                        {isCurrent && <Check className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />}
                      </button>
                    );
                  })
                )}
              </div>

              <div className="pt-2 mt-2 border-t border-slate-200 dark:border-slate-800">
                <button
                  onClick={() => {
                    setIsDropdownOpen(false);
                    setIsCreateModalOpen(true);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-500/10 hover:text-indigo-700 dark:hover:text-indigo-300 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  Create New Team
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Action Buttons */}
        <div className="flex items-center gap-2.5 ml-auto">
          {activeTeam && (
            <button
              onClick={() => setIsInviteModalOpen(true)}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 border border-slate-300/80 text-slate-700 hover:text-slate-900 dark:bg-slate-800/80 dark:hover:bg-slate-700/80 dark:border-slate-700/60 dark:text-slate-200 dark:hover:text-white text-xs font-medium transition-colors"
            >
              <UserPlus className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              Invite Member
            </button>
          )}

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-all shadow-lg shadow-indigo-600/20"
          >
            <Plus className="w-3.5 h-3.5" />
            Create Team
          </button>
        </div>
      </div>

      {/* Navigation Tabs (only shown when an active team is selected) */}
      {activeTeam && (
        <div className="flex items-center gap-1.5 border-b border-slate-200 dark:border-slate-800/80 pb-2 px-1 overflow-x-auto">
          {navTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <NavLink
                key={tab.path}
                to={tab.path}
                end={tab.exact}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-sm dark:bg-indigo-500/15 dark:text-indigo-300 dark:border-indigo-500/30'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.name}
              </NavLink>
            );
          })}
        </div>
      )}

      {/* Modals */}
      <CreateTeamModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />

      {activeTeam && (
        <InviteMemberModal
          isOpen={isInviteModalOpen}
          onClose={() => setIsInviteModalOpen(false)}
        />
      )}
    </div>
  );
};
