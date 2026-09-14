import React from 'react';
import { useThemeStore } from '../../store/useThemeStore';

/**
 * AmbientCanvas creates the signature atmospheric background layer for Ambient Focus.
 * It renders large, extremely slow blurred gradient fields positioned around the screen
 * with a dark central vignette to ensure code and text remain crisp and readable.
 */
export const AmbientCanvas: React.FC = () => {
  const { resolvedTheme, reduceMotion } = useThemeStore();

  if (resolvedTheme !== 'ambient') {
    return null;
  }

  return (
    <div
      className="fixed inset-0 pointer-events-none z-0 overflow-hidden select-none"
      aria-hidden="true"
      style={{
        background: '#060813',
      }}
    >
      {/* Orb 1: Deep Indigo / Violet (Top-Left) */}
      <div
        className={`absolute -top-32 -left-32 w-[650px] h-[650px] rounded-full filter blur-[100px] opacity-60 ${
          reduceMotion ? '' : 'ambient-orb-1'
        }`}
        style={{
          background: 'radial-gradient(circle, rgba(79, 70, 229, 0.28) 0%, rgba(49, 46, 129, 0.18) 50%, rgba(6, 8, 19, 0) 75%)',
        }}
      />

      {/* Orb 2: Deep Cyan / Teal (Top-Right) */}
      <div
        className={`absolute -top-40 right-[-10%] w-[700px] h-[700px] rounded-full filter blur-[120px] opacity-50 ${
          reduceMotion ? '' : 'ambient-orb-2'
        }`}
        style={{
          background: 'radial-gradient(circle, rgba(6, 182, 212, 0.22) 0%, rgba(15, 118, 110, 0.14) 50%, rgba(6, 8, 19, 0) 75%)',
        }}
      />

      {/* Orb 3: Violet / Purple (Bottom-Right) */}
      <div
        className={`absolute -bottom-48 right-[15%] w-[800px] h-[800px] rounded-full filter blur-[130px] opacity-55 ${
          reduceMotion ? '' : 'ambient-orb-3'
        }`}
        style={{
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.22) 0%, rgba(76, 29, 149, 0.14) 50%, rgba(6, 8, 19, 0) 75%)',
        }}
      />

      {/* Orb 4: Deep Blue / Navy (Bottom-Left) */}
      <div
        className="absolute -bottom-40 -left-20 w-[600px] h-[600px] rounded-full filter blur-[110px] opacity-40"
        style={{
          background: 'radial-gradient(circle, rgba(30, 58, 138, 0.25) 0%, rgba(15, 23, 42, 0) 70%)',
        }}
      />

      {/* Central Calm Vignette Mask: Darkens center content area for high readability */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 45%, rgba(6, 8, 19, 0.45) 0%, rgba(6, 8, 19, 0.85) 100%)',
        }}
      />
    </div>
  );
};
