import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { WorkspaceUpdate } from '../../api/workspaces';
import {
  Settings, ArrowLeft, Loader2, Check, Trash2, Database, Wrench, Cpu,
  Eye, EyeOff, Plus, X, AlertTriangle
} from 'lucide-react';

const AI_MODELS = [
  { value: 'gemini-3.6-flash', label: 'Gemini 3.6 Flash (Recommended)', provider: 'Google' },
  { value: 'gpt-4o', label: 'GPT-4o', provider: 'OpenAI' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo', provider: 'OpenAI' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', provider: 'OpenAI' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
  { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus', provider: 'Anthropic' },
  { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro', provider: 'Google' },
  { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash', provider: 'Google' },
];

const SectionCard: React.FC<{ title: string; description: string; icon: React.ReactNode; children: React.ReactNode }> = ({ title, description, icon, children }) => (
  <div className="bg-[#0f141f] border border-slate-800/80 rounded-2xl p-6 shadow-xl">
    <div className="flex items-center gap-3 mb-1">
      <div className="text-indigo-400">{icon}</div>
      <h2 className="text-lg font-semibold text-white">{title}</h2>
    </div>
    <p className="text-slate-400 text-sm mb-6">{description}</p>
    {children}
  </div>
);

type EnvVar = { key: string; value: string; masked: boolean };

export const WorkspaceSettingsPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const justCreated = searchParams.get('created') === 'true';

  const { workspaces, updateWorkspace, deleteWorkspace, fetchWorkspaces, setActiveWorkspace, activeWorkspaceId } = useWorkspaceStore();

  const workspace = workspaces.find(w => w.id === workspaceId);

  const [formData, setFormData] = useState<WorkspaceUpdate>({});
  const [envVars, setEnvVars] = useState<EnvVar[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteInput, setDeleteInput] = useState('');
  const [success, setSuccess] = useState(justCreated);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!workspace && workspaces.length === 0) {
      fetchWorkspaces();
    }
  }, [workspace, workspaces.length, fetchWorkspaces]);

  useEffect(() => {
    if (workspace) {
      setFormData({
        name: workspace.name,
        description: workspace.description || '',
        default_ai_model: workspace.default_ai_model,
        vector_db_config: workspace.vector_db_config,
        tool_config: workspace.tool_config,
      });
      const existing = Object.entries(workspace.tool_config || {}).map(([key, value]) => ({
        key, value: String(value), masked: true
      }));
      setEnvVars(existing.length > 0 ? existing : []);
    }
  }, [workspace]);

  useEffect(() => {
    if (success) {
      const t = setTimeout(() => setSuccess(false), 4000);
      return () => clearTimeout(t);
    }
  }, [success]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const addEnvVar = () => setEnvVars(prev => [...prev, { key: '', value: '', masked: false }]);
  const removeEnvVar = (i: number) => setEnvVars(prev => prev.filter((_, idx) => idx !== i));
  const updateEnvVar = (i: number, field: 'key' | 'value', val: string) =>
    setEnvVars(prev => prev.map((ev, idx) => idx === i ? { ...ev, [field]: val } : ev));
  const toggleMask = (i: number) => setEnvVars(prev => prev.map((ev, idx) => idx === i ? { ...ev, masked: !ev.masked } : ev));

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;
    setSaveError(null);
    setIsSaving(true);
    try {
      const envVarObj = Object.fromEntries(envVars.filter(ev => ev.key.trim()).map(ev => [ev.key.trim(), ev.value]));
      await updateWorkspace(workspaceId, { ...formData, tool_config: envVarObj });
      setSuccess(true);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to save settings.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!workspaceId || deleteInput !== workspace?.name) return;
    setIsDeleting(true);
    try {
      await deleteWorkspace(workspaceId);
      navigate('/workspaces');
    } finally {
      setIsDeleting(false);
    }
  };

  if (!workspace) {
    return (
      <div className="flex flex-col items-center justify-center py-32">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mb-4" />
        <p className="text-slate-400">Loading workspace settings...</p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto w-full h-full overflow-y-auto">
      <div className="mb-8">
        <button onClick={() => navigate('/workspaces')} className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors mb-6">
          <ArrowLeft className="w-4 h-4" /> Back to Workspaces
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <Settings className="w-7 h-7 text-indigo-400" />
              {workspace.name}
            </h1>
            <p className="text-slate-400 mt-1">Configure settings for this workspace.</p>
          </div>
          {workspace.id !== activeWorkspaceId && (
            <button onClick={() => setActiveWorkspace(workspace.id)} className="px-4 py-2 text-sm font-medium text-indigo-400 bg-indigo-500/10 hover:bg-indigo-600/20 border border-indigo-500/30 rounded-xl transition-all">
              Set as Active
            </button>
          )}
        </div>
      </div>

      <form onSubmit={handleSave} className="flex flex-col gap-6">
        {/* General Settings */}
        <SectionCard title="General" description="Basic workspace information." icon={<Settings className="w-5 h-5" />}>
          {saveError && <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">{saveError}</div>}
          {success && (
            <div className="mb-4 p-3 bg-green-500/10 border border-green-500/20 rounded-xl text-green-400 text-sm flex items-center gap-2">
              <Check className="w-4 h-4" />
              {justCreated ? 'Workspace created! Configure your settings below.' : 'Settings saved successfully.'}
            </div>
          )}
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-slate-300">Workspace Name</label>
              <input type="text" name="name" value={formData.name || ''} onChange={handleChange}
                className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium text-slate-300">Description</label>
              <textarea name="description" value={formData.description || ''} onChange={handleChange} rows={3}
                className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all resize-none" />
            </div>
          </div>
        </SectionCard>

        {/* AI Configuration */}
        <SectionCard title="AI Configuration" description="Set the default model for AI-powered operations in this workspace." icon={<Cpu className="w-5 h-5" />}>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Default AI Model</label>
            <select name="default_ai_model" value={formData.default_ai_model || 'gpt-4o'} onChange={handleChange}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all appearance-none">
              {AI_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label} ({m.provider})</option>
              ))}
            </select>
          </div>
        </SectionCard>

        {/* Vector DB Configuration */}
        <SectionCard title="Vector DB Configuration" description="Configure the vector database connection for this workspace (JSON format)." icon={<Database className="w-5 h-5" />}>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-300">Configuration (JSON)</label>
            <textarea
              value={JSON.stringify(formData.vector_db_config || {}, null, 2)}
              onChange={e => {
                try { setFormData(prev => ({ ...prev, vector_db_config: JSON.parse(e.target.value) })); } catch { /* let user finish typing */ }
              }}
              rows={5}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all resize-none"
            />
          </div>
        </SectionCard>

        {/* Environment Variables */}
        <SectionCard title="Environment Variables" description="Securely store API keys and configuration values for this workspace." icon={<Wrench className="w-5 h-5" />}>
          <div className="flex flex-col gap-3">
            {envVars.map((ev, i) => (
              <div key={i} className="flex items-center gap-2">
                <input type="text" value={ev.key} onChange={e => updateEnvVar(i, 'key', e.target.value)}
                  placeholder="KEY"
                  className="flex-1 bg-slate-900/50 border border-slate-700 rounded-xl px-3 py-2 text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all" />
                <div className="relative flex-[2]">
                  <input
                    type={ev.masked ? 'password' : 'text'}
                    value={ev.value}
                    onChange={e => updateEnvVar(i, 'value', e.target.value)}
                    placeholder="value"
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-3 py-2 pr-9 text-white text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all"
                  />
                  <button type="button" onClick={() => toggleMask(i)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
                    {ev.masked ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <button type="button" onClick={() => removeEnvVar(i)} className="p-2 text-slate-600 hover:text-red-400 transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
            <button type="button" onClick={addEnvVar}
              className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 mt-2 transition-colors w-fit">
              <Plus className="w-4 h-4" /> Add Variable
            </button>
          </div>
        </SectionCard>

        {/* Save */}
        <div className="flex items-center justify-end gap-3">
          <button type="button" onClick={() => navigate('/workspaces')} className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-xl transition-all">
            Cancel
          </button>
          <button type="submit" disabled={isSaving}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-2 disabled:opacity-70">
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            Save Settings
          </button>
        </div>
      </form>

      {/* Danger Zone */}
      <div className="mt-6 bg-[#0f141f] border border-red-900/30 rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-1">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-semibold text-red-400">Danger Zone</h2>
        </div>
        <p className="text-slate-400 text-sm mb-4">Permanently delete this workspace and all its repositories. This action cannot be undone.</p>
        {!showDeleteConfirm ? (
          <button onClick={() => setShowDeleteConfirm(true)} className="px-4 py-2 bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-500/30 text-sm font-medium rounded-xl transition-all">
            Delete Workspace
          </button>
        ) : (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-slate-300">Type <span className="font-mono text-red-400 font-semibold">{workspace.name}</span> to confirm:</p>
            <input
              type="text"
              value={deleteInput}
              onChange={e => setDeleteInput(e.target.value)}
              placeholder={workspace.name}
              className="bg-slate-900/50 border border-red-800/50 focus:border-red-500/60 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-red-500/30 transition-all"
            />
            <div className="flex gap-3">
              <button onClick={() => { setShowDeleteConfirm(false); setDeleteInput(''); }}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm rounded-xl transition-colors">
                Cancel
              </button>
              <button onClick={handleDelete} disabled={isDeleting || deleteInput !== workspace.name}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-medium rounded-xl transition-colors flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed">
                {isDeleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                Permanently Delete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
