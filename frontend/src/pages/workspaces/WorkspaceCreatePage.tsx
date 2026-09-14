import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '../../store/workspaceStore';
import { WorkspaceCreate } from '../../api/workspaces';
import { Layers, ArrowLeft, Loader2, Check } from 'lucide-react';

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

export const WorkspaceCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { createWorkspace, isLoading } = useWorkspaceStore();

  const [formData, setFormData] = useState<WorkspaceCreate>({
    name: '',
    description: null,
    default_ai_model: 'gpt-4o',
    default_repo_id: null,
    vector_db_config: {},
    tool_config: {},
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState<string | null>(null);

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!formData.name.trim()) errs.name = 'Workspace name is required.';
    else if (formData.name.length < 2) errs.name = 'Name must be at least 2 characters.';
    else if (formData.name.length > 100) errs.name = 'Name must be under 100 characters.';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSubmitError(null);
    try {
      const ws = await createWorkspace(formData);
      navigate(`/workspaces/${ws.id}/settings?created=true`);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to create workspace. Please try again.');
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto w-full h-full overflow-y-auto">
      <div className="mb-8">
        <button
          onClick={() => navigate('/workspaces')}
          className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Workspaces
        </button>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Layers className="w-7 h-7 text-indigo-400" />
          New Workspace
        </h1>
        <p className="text-slate-400 mt-1">Set up an isolated environment for your engineering project.</p>
      </div>

      <div className="bg-[#0f141f] border border-slate-800/80 rounded-2xl p-6 shadow-xl">
        {submitError && (
          <div className="mb-5 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
            {submitError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          {/* Name */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-300">
              Workspace Name <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Backend API, Mobile App, Data Pipeline"
              className={`bg-slate-900/50 border rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-600 ${
                errors.name ? 'border-red-500/60' : 'border-slate-700'
              }`}
            />
            {errors.name && <p className="text-xs text-red-400">{errors.name}</p>}
          </div>

          {/* Description */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-300">Description</label>
            <textarea
              name="description"
              value={formData.description || ''}
              onChange={handleChange}
              rows={3}
              placeholder="What is this workspace for? (optional)"
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-600 resize-none"
            />
          </div>

          {/* Default AI Model */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-300">Default AI Model</label>
            <select
              name="default_ai_model"
              value={formData.default_ai_model}
              onChange={handleChange}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all appearance-none"
            >
              {AI_MODELS.map(m => (
                <option key={m.value} value={m.value}>{m.label} ({m.provider})</option>
              ))}
            </select>
            <p className="text-xs text-slate-500">This model will be used by default for AI operations in this workspace.</p>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800/60">
            <button
              type="button"
              onClick={() => navigate('/workspaces')}
              className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-xl transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Create Workspace
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
