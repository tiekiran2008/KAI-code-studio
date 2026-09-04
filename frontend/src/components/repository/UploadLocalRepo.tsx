import React, { useState } from 'react';
import { Upload, RefreshCw } from 'lucide-react';

interface UploadLocalRepoProps {
  onUpload: (name: string, file?: File) => Promise<void>;
  isUploading: boolean;
}

export const UploadLocalRepo: React.FC<UploadLocalRepoProps> = ({ onUpload, isUploading }) => {
  const [repoName, setRepoName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!repoName) {
        setRepoName(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onUpload(repoName || 'local-repo', selectedFile || undefined);
    setRepoName('');
    setSelectedFile(null);
  };

  return (
    <div className="glass-panel p-8 rounded-2xl max-w-2xl mx-auto space-y-6">
      <div className="space-y-1">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Upload className="w-5 h-5 text-indigo-400" /> Upload Local Codebase
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          Upload local project ZIP archives or folders directly to index offline codebases into the local vector DB.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-slate-300">Repository Name</label>
          <input
            type="text"
            required
            placeholder="my-local-project"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="border-2 border-dashed border-slate-700 rounded-2xl p-8 flex flex-col items-center justify-center gap-3 bg-slate-900/40 hover:bg-slate-900/80 transition-colors cursor-pointer relative group">
          <input
            type="file"
            onChange={handleFileChange}
            className="absolute inset-0 opacity-0 cursor-pointer"
          />
          <Upload className="w-8 h-8 text-indigo-400 group-hover:scale-110 transition-transform" />
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-200">
              {selectedFile ? selectedFile.name : 'Select or drop project ZIP / folder here'}
            </p>
            <p className="text-xs text-slate-500">Supports .zip, .tar.gz or code archives</p>
          </div>
        </div>

        <button
          type="submit"
          disabled={isUploading}
          className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm shadow-glow flex items-center justify-center gap-2 transition-all disabled:opacity-50"
        >
          {isUploading ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" /> Uploading & Indexing...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" /> Start Ingestion Pipeline
            </>
          )}
        </button>
      </form>
    </div>
  );
};
