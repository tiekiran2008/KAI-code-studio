import React, { useState } from 'react';
import { useTeamStore } from '../../store/teamStore';
import { Settings, Save, AlertTriangle, Trash2, ArrowRight } from 'lucide-react';

export const TeamSettingsPage: React.FC = () => {
  const { activeTeam, updateTeam, transferOwnership, deleteTeam } = useTeamStore();
  const [name, setName] = useState(activeTeam?.name || '');
  const [description, setDescription] = useState(activeTeam?.description || '');
  const [isSaving, setIsSaving] = useState(false);
  const [newOwnerId, setNewOwnerId] = useState('');
  const [isTransferring, setIsTransferring] = useState(false);

  if (!activeTeam) {
    return <div className="text-gray-500 text-center p-8">No Active Team</div>;
  }

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await updateTeam(activeTeam.id, { name, description });
      // Optionally show success toast
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
      } catch (err) {
        console.error(err);
      }
    }
  };

  return (
    <div className="h-full max-w-4xl mx-auto flex flex-col gap-6 animate-in fade-in duration-300">
      <div className="flex items-center gap-3 mb-2">
        <Settings className="w-8 h-8 text-indigo-400" />
        <h1 className="text-3xl font-bold text-white">Team Settings</h1>
      </div>

      <div className="bg-gray-900/40 rounded-2xl border border-gray-800/50 overflow-hidden">
        <div className="p-6 border-b border-gray-800/50">
          <h2 className="text-lg font-semibold text-white mb-1">General Profile</h2>
          <p className="text-sm text-gray-400">Update your team's name and description.</p>
        </div>
        <form onSubmit={handleUpdate} className="p-6 space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Team Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-4 py-2 bg-gray-950/50 border border-gray-700/50 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500/50 max-w-md block"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-4 py-2 bg-gray-950/50 border border-gray-700/50 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500/50 max-w-md block"
            />
          </div>
          <div>
            <button
              type="submit"
              disabled={isSaving || (name === activeTeam.name && description === activeTeam.description)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      <div className="bg-gray-900/40 rounded-2xl border border-gray-800/50 overflow-hidden">
        <div className="p-6 border-b border-gray-800/50">
          <h2 className="text-lg font-semibold text-white mb-1">Ownership Transfer</h2>
          <p className="text-sm text-gray-400">Transfer this team to another user.</p>
        </div>
        <div className="p-6">
          <div className="flex gap-4 items-end">
            <div className="space-y-2 flex-1 max-w-sm">
              <label className="text-sm font-medium text-gray-300">New Owner's User ID</label>
              <input
                type="text"
                value={newOwnerId}
                onChange={(e) => setNewOwnerId(e.target.value)}
                placeholder="user_id"
                className="w-full px-4 py-2 bg-gray-950/50 border border-gray-700/50 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-indigo-500/50"
              />
            </div>
            <button
              onClick={handleTransfer}
              disabled={isTransferring || !newOwnerId}
              className="flex items-center gap-2 px-4 py-2 bg-orange-500/10 text-orange-400 hover:bg-orange-500/20 border border-orange-500/20 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
            >
              Transfer <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-orange-400/80 mt-3 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            This action requires confirmation and is irreversible unless the new owner transfers it back.
          </p>
        </div>
      </div>

      <div className="bg-rose-500/5 rounded-2xl border border-rose-500/20 overflow-hidden">
        <div className="p-6 border-b border-rose-500/10">
          <h2 className="text-lg font-semibold text-rose-400 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Danger Zone
          </h2>
          <p className="text-sm text-rose-400/70">Irreversible destructive actions.</p>
        </div>
        <div className="p-6 flex items-center justify-between">
          <div>
            <h3 className="text-white font-medium mb-1">Delete Team</h3>
            <p className="text-sm text-gray-400">Permanently delete this team and all of its resources.</p>
          </div>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 px-4 py-2 bg-rose-500 hover:bg-rose-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete Team
          </button>
        </div>
      </div>
    </div>
  );
};
