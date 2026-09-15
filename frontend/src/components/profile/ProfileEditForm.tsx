import React, { useState, useRef, useEffect } from 'react';
import { useProfileStore } from '../../store/profileStore';
import { UserProfile } from '../../api/profile';
import { deleteSupabaseStorageAvatar } from '../../lib/supabaseStorage';
import { User, Camera, Globe, Palette, Cpu, Bell, Loader2, Check, Trash2, AlertTriangle } from 'lucide-react';

interface ProfileEditFormProps {
  initialData: UserProfile;
  onSave: () => void;
}

export const ProfileEditForm: React.FC<ProfileEditFormProps> = ({ initialData, onSave }) => {
  const [formData, setFormData] = useState<Partial<UserProfile>>({
    name: initialData.name || '',
    bio: initialData.bio || '',
    timezone: initialData.timezone || 'UTC',
    theme_preference: initialData.theme_preference || 'system',
    preferred_llm_provider: initialData.preferred_llm_provider || 'openai',
    default_ai_model: initialData.default_ai_model || 'gpt-4o',
    notification_preferences: {
      email: initialData.notification_preferences?.email ?? true,
      in_app: initialData.notification_preferences?.in_app ?? true,
    }
  });

  const [avatarPreview, setAvatarPreview] = useState<string | null>(initialData.avatar);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { updateProfile, removeAvatar, isSaving, isRemovingAvatar, error, clearError } = useProfileStore();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleNotificationChange = (key: 'email' | 'in_app') => {
    setFormData(prev => ({
      ...prev,
      notification_preferences: {
        ...prev.notification_preferences!,
        [key]: !prev.notification_preferences![key]
      }
    }));
  };

  useEffect(() => {
    setAvatarPreview(initialData.avatar);
    setFormData({
      name: initialData.name || '',
      bio: initialData.bio || '',
      timezone: initialData.timezone || 'UTC',
      theme_preference: initialData.theme_preference || 'system',
      preferred_llm_provider: initialData.preferred_llm_provider || 'openai',
      default_ai_model: initialData.default_ai_model || 'gpt-4o',
      notification_preferences: {
        email: initialData.notification_preferences?.email ?? true,
        in_app: initialData.notification_preferences?.in_app ?? true,
      }
    });
  }, [initialData]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setFileError(null);
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        setFileError('File size exceeds 2MB limit. Please choose a smaller image.');
        return;
      }
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result as string;
        setAvatarPreview(base64String);
        setFormData(prev => ({ ...prev, avatar: base64String }));
      };
      reader.onerror = () => {
        setFileError('Failed to read image file.');
      };
      reader.readAsDataURL(file);
    }
  };

  const handleCancel = () => {
    setFormData({
      name: initialData.name || '',
      bio: initialData.bio || '',
      timezone: initialData.timezone || 'UTC',
      theme_preference: initialData.theme_preference || 'system',
      preferred_llm_provider: initialData.preferred_llm_provider || 'openai',
      default_ai_model: initialData.default_ai_model || 'gpt-4o',
      notification_preferences: {
        email: initialData.notification_preferences?.email ?? true,
        in_app: initialData.notification_preferences?.in_app ?? true,
      }
    });
    setAvatarPreview(initialData.avatar);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    setFileError(null);
    setRemoveError(null);
    setShowRemoveConfirm(false);
    clearError();
  };

  const handleConfirmRemovePhoto = async () => {
    setRemoveError(null);
    clearError();
    try {
      // 1. Delete from Supabase Storage if applicable
      const oldAvatar = initialData.avatar || avatarPreview;
      if (oldAvatar) {
        await deleteSupabaseStorageAvatar(oldAvatar);
      }

      // 2. Remove avatar in profile store & backend
      await removeAvatar();

      // 3. Reset local form and preview states
      setAvatarPreview(null);
      setFormData(prev => ({ ...prev, avatar: null }));
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      setShowRemoveConfirm(false);
      setSuccessMessage('Profile photo removed successfully');
      onSave();
    } catch (err: any) {
      setRemoveError(err.message || 'Failed to remove profile photo. Please try again.');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      await updateProfile(formData);
      setSuccessMessage('Profile saved successfully');
      onSave();
    } catch {
      // Error handled in store
    }
  };

  return (
    <>
      <form onSubmit={handleSubmit} className="flex flex-col gap-8 max-w-3xl">
        {(error || fileError) && !showRemoveConfirm && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
            {fileError || error}
          </div>
        )}


        {/* Avatar Section */}
        <div className="flex items-center gap-6 pb-8 border-b border-slate-800/60">
          <div className="relative group">
            <div className="w-24 h-24 rounded-full overflow-hidden bg-slate-800 border-2 border-slate-700 flex items-center justify-center">
              {avatarPreview ? (
                <img src={avatarPreview} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                <User className="w-10 h-10 text-slate-500" />
              )}
            </div>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isSaving || isRemovingAvatar}
              className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-full flex items-center justify-center text-white disabled:opacity-0"
              aria-label="Upload photo"
            >
              <Camera className="w-6 h-6" />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/*"
              className="hidden"
            />
          </div>
          <div>
            <h3 className="text-lg font-medium text-white mb-1">Profile Picture</h3>
            <p className="text-sm text-slate-400 mb-3">Upload a new avatar. Max size 2MB.</p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isSaving || isRemovingAvatar}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-sm text-white rounded-lg transition-colors border border-slate-700 hover:border-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Choose Image
              </button>
              {avatarPreview && (
                <button
                  type="button"
                  id="btn-remove-profile-photo"
                  onClick={() => {
                    setRemoveError(null);
                    setShowRemoveConfirm(true);
                  }}
                  disabled={isSaving || isRemovingAvatar}
                  className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-sm text-red-400 hover:text-red-300 rounded-lg transition-colors border border-red-500/20 hover:border-red-500/30 flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Trash2 className="w-4 h-4" />
                  Remove photo
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Basic Info */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <User className="w-4 h-4 text-slate-500" /> Full Name
            </label>
            <input
              type="text"
              name="name"
              value={formData.name || ''}
              onChange={handleChange}
              disabled={isSaving || isRemovingAvatar}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-600 disabled:opacity-50"
              placeholder="John Doe"
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Globe className="w-4 h-4 text-slate-500" /> Timezone
            </label>
            <select
              name="timezone"
              value={formData.timezone}
              onChange={handleChange}
              disabled={isSaving || isRemovingAvatar}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all appearance-none disabled:opacity-50"
            >
              <option value="UTC">UTC</option>
              <option value="America/New_York">Eastern Time (ET)</option>
              <option value="America/Los_Angeles">Pacific Time (PT)</option>
              <option value="Europe/London">London (GMT)</option>
              <option value="Asia/Tokyo">Tokyo (JST)</option>
            </select>
          </div>

          <div className="flex flex-col gap-2 md:col-span-2">
            <label className="text-sm font-medium text-slate-300">Bio</label>
            <textarea
              name="bio"
              value={formData.bio || ''}
              onChange={handleChange}
              disabled={isSaving || isRemovingAvatar}
              rows={3}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-600 resize-none disabled:opacity-50"
              placeholder="Tell us a little about yourself..."
            />
          </div>

          {/* Preferences */}
          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Palette className="w-4 h-4 text-slate-500" /> Theme Preference
            </label>
            <select
              name="theme_preference"
              value={formData.theme_preference}
              onChange={handleChange}
              disabled={isSaving || isRemovingAvatar}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all appearance-none disabled:opacity-50"
            >
              <option value="system">System Default</option>
              <option value="dark">Dark Mode</option>
              <option value="light">Light Mode</option>
              <option value="ambient">Ambient Focus (Signature)</option>
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-slate-500" /> Preferred LLM Provider
            </label>
            <select
              name="preferred_llm_provider"
              value={formData.preferred_llm_provider}
              onChange={handleChange}
              disabled={isSaving || isRemovingAvatar}
              className="bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all appearance-none disabled:opacity-50"
            >
              <option value="openai">OpenAI</option>
              <option value="gemini">Google Gemini</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>

          <div className="flex flex-col gap-2 md:col-span-2 pt-4 border-t border-slate-800/60">
            <label className="text-sm font-medium text-slate-300 flex items-center gap-2 mb-2">
              <Bell className="w-4 h-4 text-slate-500" /> Notification Settings
            </label>
            
            <label className="flex items-center gap-3 cursor-pointer group">
              <div className="relative flex items-center">
                <input
                  type="checkbox"
                  checked={formData.notification_preferences?.email}
                  onChange={() => handleNotificationChange('email')}
                  disabled={isSaving || isRemovingAvatar}
                  className="peer sr-only"
                />
                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-500"></div>
              </div>
              <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">Email Notifications</span>
            </label>

            <label className="flex items-center gap-3 cursor-pointer group mt-2">
              <div className="relative flex items-center">
                <input
                  type="checkbox"
                  checked={formData.notification_preferences?.in_app}
                  onChange={() => handleNotificationChange('in_app')}
                  disabled={isSaving || isRemovingAvatar}
                  className="peer sr-only"
                />
                <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-500"></div>
              </div>
              <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors">In-App Notifications</span>
            </label>
          </div>
        </div>

        <div className="flex items-center justify-end gap-4 pt-6 border-t border-slate-800/60 mt-4">
          {successMessage && (
            <span className="flex items-center gap-2 text-green-400 text-sm mr-auto">
              <Check className="w-4 h-4" /> {successMessage}
            </span>
          )}
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSaving || isRemovingAvatar}
            className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium rounded-xl transition-all disabled:opacity-70 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSaving || isRemovingAvatar}
            className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Changes
          </button>
        </div>
      </form>

      {/* Remove Photo Confirmation Modal */}
      {showRemoveConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="remove-photo-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150"
        >
          <div className="bg-[#0f141f] border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-10 h-10 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center shrink-0 text-red-400">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 id="remove-photo-title" className="text-lg font-semibold text-white">
                  Remove Profile Photo
                </h3>
                <p className="text-sm text-slate-400 mt-1">
                  Are you sure you want to remove your profile photo? Your avatar will immediately be reset to the default icon and this change will be saved.
                </p>
              </div>
            </div>

            {removeError && (
              <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs">
                {removeError}
              </div>
            )}

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => {
                  if (!isRemovingAvatar) {
                    setShowRemoveConfirm(false);
                    setRemoveError(null);
                  }
                }}
                disabled={isRemovingAvatar}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-sm text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="button"
                id="btn-confirm-remove-photo"
                onClick={handleConfirmRemovePhoto}
                disabled={isRemovingAvatar}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-sm font-medium text-white rounded-xl shadow-lg shadow-red-600/20 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRemovingAvatar && <Loader2 className="w-4 h-4 animate-spin" />}
                {isRemovingAvatar ? 'Removing...' : 'Remove Photo'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

