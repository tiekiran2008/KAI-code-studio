import React, { useEffect, useMemo, useState } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { TeamHeaderNav } from './TeamHeaderNav';
import { CreateTeamModal } from './CreateTeamModal';
import { Shield, Info, Check, Minus, Users, Plus } from 'lucide-react';
import { RoleEnum } from '../../types';

export const RoleManagementPage: React.FC = () => {
  const { activeTeam, permissionMatrix, fetchPermissionMatrix, isLoading } = useTeamStore();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  useEffect(() => {
    fetchPermissionMatrix();
  }, [fetchPermissionMatrix]);

  const roles: RoleEnum[] = ['owner', 'admin', 'maintainer', 'developer', 'reviewer', 'viewer'];

  const categories = useMemo(() => {
    const cats = new Set(permissionMatrix.map(p => p.category));
    return Array.from(cats);
  }, [permissionMatrix]);

  if (!activeTeam) {
    return (
      <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
        <TeamHeaderNav />
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center glass-panel rounded-2xl">
          <Users className="w-12 h-12 text-slate-400 dark:text-slate-600 mb-3" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">No Active Team Selected</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-sm mb-6">
            Please select or create a team using the team switcher above to view roles and permissions.
          </p>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Team
          </button>
        </div>
        <CreateTeamModal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
        />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300 overflow-hidden">
      <TeamHeaderNav />

      <div className="glass-panel flex items-center justify-between p-6 rounded-2xl flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3 mb-1">
            <Shield className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            Roles & Permissions
          </h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">
            RBAC matrix defining access levels and administrative capabilities for {activeTeam.name}.
          </p>
        </div>
      </div>

      <div className="flex-1 glass-card rounded-2xl overflow-hidden flex flex-col">
        {isLoading && permissionMatrix.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500 dark:text-slate-400 text-sm">Loading permission matrix...</div>
        ) : (
          <div className="overflow-auto custom-scrollbar flex-1 relative">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead className="sticky top-0 z-10 bg-slate-100/95 dark:bg-slate-950/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
                <tr>
                  <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 w-1/4">Permission</th>
                  {roles.map(role => (
                    <th key={role} className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300 text-center capitalize w-[12%]">
                      {role}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60">
                {categories.map(category => (
                  <React.Fragment key={category}>
                    <tr className="bg-slate-100/80 dark:bg-slate-900/60">
                      <td colSpan={roles.length + 1} className="px-6 py-2.5 text-[11px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                        {category}
                      </td>
                    </tr>
                    {permissionMatrix
                      .filter(p => p.category === category)
                      .map((row) => (
                        <tr key={row.permission} className="hover:bg-slate-50/80 dark:hover:bg-slate-900/30 transition-colors">
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-slate-900 dark:text-slate-200">{row.permission}</div>
                            <div className="text-xs text-slate-500 mt-0.5 flex items-start gap-1">
                              <Info className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-400 dark:text-slate-500" />
                              {row.description}
                            </div>
                          </td>
                          {roles.map(role => (
                            <td key={role} className="px-6 py-4 text-center">
                              {row.roles[role] ? (
                                <div className="flex justify-center">
                                  <div className="w-6 h-6 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                                    <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" strokeWidth={3} />
                                  </div>
                                </div>
                              ) : (
                                <div className="flex justify-center text-slate-300 dark:text-slate-700">
                                  <Minus className="w-4 h-4" />
                                </div>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
