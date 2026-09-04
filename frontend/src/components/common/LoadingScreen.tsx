import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Spinner } from './Spinner';

interface LoadingScreenProps {
  isLoading: boolean;
  message?: string;
  fullScreen?: boolean;
}

export const LoadingScreen: React.FC<LoadingScreenProps> = ({ 
  isLoading, 
  message = 'Loading...',
  fullScreen = true
}) => {
  return (
    <AnimatePresence>
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className={`
            ${fullScreen ? 'fixed inset-0 z-[100]' : 'absolute inset-0 z-50'}
            flex flex-col items-center justify-center bg-[#090d16]/80 backdrop-blur-sm
          `}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            className="flex flex-col items-center gap-4 p-8 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-2xl"
          >
            <div className="relative">
              <div className="absolute inset-0 bg-indigo-500/20 blur-xl rounded-full" />
              <Spinner size="lg" color="text-indigo-400" />
            </div>
            
            {message && (
              <span className="text-sm font-medium text-slate-300 animate-pulse">
                {message}
              </span>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
