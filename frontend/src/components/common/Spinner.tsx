import React from 'react';
import { motion } from 'framer-motion';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  color?: string;
  className?: string;
}

export const Spinner: React.FC<SpinnerProps> = ({ 
  size = 'md', 
  color = 'text-indigo-500',
  className = '' 
}) => {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
    xl: 'w-12 h-12 border-4'
  };

  return (
    <motion.div
      className={`rounded-full border-t-transparent ${sizeMap[size]} ${color} ${className}`}
      style={{ borderStyle: 'solid', borderTopColor: 'transparent', borderRightColor: 'currentColor', borderBottomColor: 'currentColor', borderLeftColor: 'currentColor' }}
      animate={{ rotate: 360 }}
      transition={{
        duration: 1,
        repeat: Infinity,
        ease: 'linear'
      }}
    />
  );
};
