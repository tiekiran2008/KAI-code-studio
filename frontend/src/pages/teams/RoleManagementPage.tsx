import React, { useEffect, useMemo } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { Shield, Info, Check, Minus } from 'lucide-react';
import { RoleEnum } from '../../types';

export const RoleManagementPage: React.FC = () => {
  const { activeTeam, permissionMatrix, fetchPermissionMatrix, isLoading } = useTeamStore();

  useEffect(() => {
    fetchPermissionMatrix();
  }, [fetchPermissionMatrix]);

  const roles: RoleEnum[] = ['owner', 'admin', 'maintainer', 'developer', 'reviewer', 'viewer'];

  const categories = useMemo(() => {
    const cats = new Set(permissionMatrix.map(p => p.category));
    return Array.from(cats);
  }, [permissionMatrix]);

  if (!activeTeam) {
    return <div className="text-gray-500 text-center p-8">No Active Team</div>;
  }

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300 overflow-hidden">
      <div className="flex items-center justify-between bg-gray-900/40 p-6 rounded-2xl border border-gray-800/50 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3 mb-2">
            <Shield className="w-6 h-6 text-indigo-400" />
            Roles & Permissions
          </h1>
          <p className="text-gray-400">
            View the access levels and capabilities for each role in {activeTeam.name}.
          </p>
        </div>
      </div>

      <div className="flex-1 bg-gray-900/40 rounded-2xl border border-gray-800/50 overflow-hidden flex flex-col">
        {isLoading && permissionMatrix.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">Loading permission matrix...</div>
        ) : (
          <div className="overflow-auto custom-scrollbar flex-1 relative">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead className="sticky top-0 z-10 bg-gray-950/90 backdrop-blur-sm border-b border-gray-800">
                <tr>
                  <th className="px-6 py-4 text-sm font-medium text-white w-1/4">Permission</th>
                  {roles.map(role => (
                    <th key={role} className="px-6 py-4 text-sm font-medium text-gray-300 text-center capitalize w-[12%]">
                      {role}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/50">
                {categories.map(category => (
                  <React.Fragment key={category}>
                    <tr className="bg-gray-800/30">
                      <td colSpan={roles.length + 1} className="px-6 py-3 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                        {category}
                      </td>
                    </tr>
                    {permissionMatrix
                      .filter(p => p.category === category)
                      .map((row) => (
                        <tr key={row.permission} className="hover:bg-gray-800/10 transition-colors">
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-200">{row.permission}</div>
                            <div className="text-xs text-gray-500 mt-1 flex items-start gap-1">
                              <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                              {row.description}
                            </div>
                          </td>
                          {roles.map(role => (
                            <td key={role} className="px-6 py-4 text-center">
                              {row.roles[role] ? (
                                <div className="flex justify-center">
                                  <div className="w-6 h-6 rounded-full bg-emerald-500/10 flex items-center justify-center">
                                    <Check className="w-3.5 h-3.5 text-emerald-400" strokeWidth={3} />
                                  </div>
                                </div>
                              ) : (
                                <div className="flex justify-center text-gray-600">
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
