import React, { useEffect } from 'react';
import { useProfileStore } from '../store/profileStore';
import { ProfileEditForm } from '../components/profile/ProfileEditForm';
import { Settings, User, Loader2 } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { profile, isLoading, fetchProfile, error } = useProfileStore();

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  return (
    <div className="p-8 max-w-5xl mx-auto w-full h-full overflow-y-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <User className="w-7 h-7 text-indigo-400" />
            Profile Settings
          </h1>
          <p className="text-slate-400 mt-1">Manage your personal information and preferences.</p>
        </div>
        <div className="hidden sm:flex items-center justify-center w-12 h-12 rounded-xl bg-slate-800/50 border border-slate-700/50">
          <Settings className="w-6 h-6 text-slate-400" />
        </div>
      </div>

      <div className="bg-[#0f141f] border border-slate-800/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        {/* Decorative background element */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-[80px] pointer-events-none" />
        
        {isLoading && !profile ? (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mb-4" />
            <p className="text-slate-400">Loading your profile...</p>
          </div>
        ) : error && !profile ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
              <Settings className="w-6 h-6 text-red-400" />
            </div>
            <p className="text-red-400 mb-2 font-medium">Failed to load profile</p>
            <p className="text-slate-500 text-sm max-w-md">{error}</p>
            <button 
              onClick={() => fetchProfile()}
              className="mt-6 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : profile ? (
          <ProfileEditForm initialData={profile} onSave={() => fetchProfile()} />
        ) : null}
      </div>
    </div>
  );
};
