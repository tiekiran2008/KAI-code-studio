import React, { useState, useEffect } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { TeamHeaderNav } from './TeamHeaderNav';
import { CreateTeamModal } from './CreateTeamModal';
import { Settings, Save, AlertTriangle, Trash2, ArrowRight, Users, Plus, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const TeamSettingsPage: React.FC = () => {
  const { activeTeam, updateTeam, transferOwnership, deleteTeam } = useTeamStore();
  const [name, setName] = useState(activeTeam?.name || '');
  const [description, setDescription] = useState(activeTeam?.description || '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [newOwnerId, setNewOwnerId] = useState('');
  const [isTransferring, setIsTransferring] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (activeTeam) {
      setName(activeTeam.name);
      setDescription(activeTeam.description || '');
    }
  }, [activeTeam]);

  if (!activeTeam) {
    return (
      <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300">
        <TeamHeaderNav />
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center glass-panel rounded-2xl">
          <Users className="w-12 h-12 text-slate-400 dark:text-slate-600 mb-3" />
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-1">No Active Team Selected</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-sm mb-6">
            Please select or create a team using the team switcher above to manage settings.
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

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      await updateTeam(activeTeam.id, { name, description });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTransfer = async () => {
    if (!newOwnerId) return;
    if (confirm('Are you sure you want to transfer ownership? You will lose Owner privileges.')) {
      setIsTransferring(true);
      try {
        await transferOwnership(activeTeam.id, newOwnerId);
        setNewOwnerId('');
      } catch (err) {
        console.error(err);
      } finally {
        setIsTransferring(false);
      }
    }
  };

  const handleDelete = async () => {
    if (confirm('DANGER: This action cannot be undone. All team data, members, and resources will be permanently deleted. Are you absolutely sure?')) {
      try {
        await deleteTeam(activeTeam.id);
        navigate('/teams');
      } catch (err) {
        console.error(err);
      }
    }
  };

  return (
    <div className="h-full flex flex-col gap-6 animate-in fade-in duration-300 overflow-y-auto custom-scrollbar">
      <TeamHeaderNav />

      <div className="max-w-4xl w-full mx-auto space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">Team Settings</h1>
            <p className="text-slate-500 dark:text-slate-400 text-xs">Configure profile, ownership, and organization details for {activeTeam.name}</p>
          </div>
        </div>

        {/* General Profile */}
        <div className="glass-card rounded-2xl overflow-hidden shadow-lg">
          <div className="p-6 border-b border-slate-200 dark:border-slate-800/80">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-0.5">General Profile</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Update your team's display name and purpose.</p>
          </div>
          <form onSubmit={handleUpdate} className="p-6 space-y-5">
            <div className="space-y-1.5 max-w-md">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">Team Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-950/60 border border-slate-300 dark:border-slate-700/60 rounded-xl text-sm text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500/60 block"
              />
            </div>
            <div className="space-y-1.5 max-w-md">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-950/60 border border-slate-300 dark:border-slate-700/60 rounded-xl text-sm text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500/60 block resize-none"
              />
            </div>
            <div className="flex items-center gap-3 pt-2">
              <button
                type="submit"
                disabled={isSaving || (name === activeTeam.name && description === (activeTeam.description || ''))}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-sm font-medium transition-colors shadow-lg shadow-indigo-600/20"
              >
                <Save className="w-4 h-4" />
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
              {saveSuccess && (
                <span className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium animate-in fade-in">
                  <Check className="w-4 h-4" />
                  Saved successfully
                </span>
              )}
            </div>
          </form>
        </div>

        {/* Ownership Transfer */}
        <div className="glass-card rounded-2xl overflow-hidden shadow-lg">
          <div className="p-6 border-b border-slate-200 dark:border-slate-800/80">
            <h2 className="text-base font-semibold text-slate-900 dark:text-white mb-0.5">Ownership Transfer</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Transfer organizational leadership and full administrative permissions to another member.</p>
          </div>
          <div className="p-6">
            <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
              <div className="space-y-1.5 flex-1 max-w-sm">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">New Owner User ID</label>
                <input
                  type="text"
                  value={newOwnerId}
                  onChange={(e) => setNewOwnerId(e.target.value)}
                  placeholder="e.g. user_123 or member email"
                  className="w-full px-3.5 py-2 bg-slate-50 dark:bg-slate-950/60 border border-slate-300 dark:border-slate-700/60 rounded-xl text-sm text-slate-900 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500/60"
                />
              </div>
              <button
                onClick={handleTransfer}
                disabled={isTransferring || !newOwnerId.trim()}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-amber-500/10 text-amber-700 dark:text-amber-300 hover:bg-amber-500/20 border border-amber-500/30 disabled:opacity-50 rounded-xl text-sm font-medium transition-colors"
              >
                <span>Transfer</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-amber-600 dark:text-amber-400/80 mt-3 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              Ownership transfer is irreversible unless the newly designated owner assigns it back to you.
            </p>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-rose-500/5 rounded-2xl border border-rose-500/20 overflow-hidden shadow-lg shadow-black/5 dark:shadow-black/20">
          <div className="p-6 border-b border-rose-500/10">
            <h2 className="text-base font-semibold text-rose-600 dark:text-rose-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Danger Zone
            </h2>
            <p className="text-xs text-rose-600/70 dark:text-rose-400/70">Destructive actions that cannot be undone.</p>
          </div>
          <div className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-slate-900 dark:text-white font-medium text-sm mb-0.5">Delete Team</h3>
              <p className="text-xs text-slate-600 dark:text-slate-400">Permanently delete this organization, team members, invitations, and audit histories.</p>
            </div>
            <button
              onClick={handleDelete}
              className="flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-sm font-medium transition-colors shrink-0 shadow-lg shadow-rose-600/20"
            >
              <Trash2 className="w-4 h-4" />
              Delete Team
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
