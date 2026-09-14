import React from 'react';
import { NavLink } from 'react-router-dom';
import { useUIStore } from '../../store/useUIStore';
import kaiLogo from '../../assets/branding/kai-logo.png';
import { 
  LayoutDashboard, 
  GitBranch, 
  Code2, 
  Cpu, 
  BrainCircuit, 
  Wrench, 
  BarChart3, 
  Settings as SettingsIcon,
  ChevronLeft,
  ChevronRight,
  Layers,
  FolderGit2,
  Users,
  FileSearch,
  FileText
} from 'lucide-react';

export const navItems = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Workspaces', path: '/workspaces', icon: Layers },
  { name: 'Projects', path: '/projects', icon: FolderGit2 },
  { name: 'Repository Manager', path: '/repositories', icon: GitBranch },
  { name: 'Team Collaboration', path: '/teams', icon: Users },
  { name: 'Code Review', path: '/reviews', icon: FileSearch },
  { name: 'Engineering Reports', path: '/reports', icon: FileText },
  { name: 'AI Workspace', path: '/workspace', icon: Code2 },
  { name: 'Agent Monitor', path: '/agents', icon: Cpu },
  { name: 'Memory Center', path: '/memory', icon: BrainCircuit },
  { name: 'Tool Activity', path: '/tools', icon: Wrench },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Settings', path: '/settings', icon: SettingsIcon },
];

export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  return (
    <aside
      className={`fixed top-0 bottom-0 left-0 z-40 bg-[#0f172a]/90 backdrop-blur-xl border-r border-slate-800 flex flex-col transition-all duration-300 ${
        sidebarCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800/80">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="relative w-9 h-9 shrink-0 flex items-center justify-center">
            <img
              src={kaiLogo}
              alt="KAI Code Studio Logo"
              className="w-9 h-9 object-contain drop-shadow-[0_0_8px_rgba(99,102,241,0.4)]"
            />
          </div>
          {!sidebarCollapsed && (
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight text-white flex items-center gap-1.5">
                KAI Code Studio
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono border border-indigo-500/30">
                  v1.0
                </span>
              </span>
              <span className="text-[11px] text-slate-400">Autonomous AI Engineering</span>
            </div>
          )}
        </div>
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 p-3 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 text-sm font-medium ${
                  isActive
                    ? 'bg-gradient-to-r from-indigo-600/30 to-purple-600/20 text-indigo-200 border border-indigo-500/40 shadow-glow'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-5 h-5 shrink-0" />
              {!sidebarCollapsed && <span>{item.name}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* System Status Footbar */}
      {!sidebarCollapsed && (
        <div className="p-3 m-3 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span>Multi-Agent Engine</span>
          </div>
          <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-500/20">
            READY
          </span>
        </div>
      )}
    </aside>
  );
};
