import React from 'react';
import { AlertTriangle, X, Trash2 } from 'lucide-react';
import { Repository } from '../../types';

interface DeleteRepoModalProps {
  repository: Repository | null;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  isDeleting: boolean;
}

export const DeleteRepoModal: React.FC<DeleteRepoModalProps> = ({
  repository,
  onClose,
  onConfirm,
  isDeleting,
}) => {
  if (!repository) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#0f172a] border border-rose-500/30 rounded-2xl max-w-md w-full p-6 space-y-6 shadow-2xl animate-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2 text-rose-400">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="text-lg font-bold text-white">Delete Repository</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-3 text-sm text-slate-300">
          <p>
            Are you sure you want to delete <span className="font-semibold text-white">{repository.name}</span>?
          </p>
          <p className="text-xs text-slate-400 bg-rose-950/40 border border-rose-500/20 p-3 rounded-xl">
            This action will permanently delete vector embeddings and code indices associated with this repository.
          </p>
        </div>

        <div className="flex justify-end gap-3 border-t border-slate-800 pt-4">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-slate-800 text-xs font-medium text-slate-300 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold flex items-center gap-2 transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            {isDeleting ? 'Deleting...' : 'Confirm Delete'}
          </button>
        </div>
      </div>
    </div>
  );
};
