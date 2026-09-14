import React from 'react';
import { useThemeStore, FocusArea } from '../../store/useThemeStore';

interface FocusAuraProps {
  children: React.ReactNode;
  area: FocusArea;
  className?: string;
  isGenerating?: boolean;
  isActive?: boolean;
  onClick?: () => void;
}

/**
 * FocusAura provides subtle contextual highlights to the active workspace panel
 * in the Ambient Focus theme (e.g. violet for editor, cyan for chat, indigo for review, emerald for agent).
 */
export const FocusAura: React.FC<FocusAuraProps> = ({
  children,
  area,
  className = '',
  isGenerating = false,
  isActive = false,
  onClick,
}) => {
  const { resolvedTheme, activeFocusArea, setActiveFocusArea } = useThemeStore();

  const isCurrentActive = isActive || activeFocusArea === area;
  const isAmbient = resolvedTheme === 'ambient';

  const handleClick = (e: React.MouseEvent) => {
    if (area && activeFocusArea !== area) {
      setActiveFocusArea(area);
    }
    if (onClick) {
      onClick();
    }
  };

  const areaClass = area ? `focus-aura-${area}` : '';
  const activeClass = isCurrentActive && isAmbient ? 'focus-aura-active' : '';
  const generatingClass = isGenerating && isAmbient ? 'ambient-ai-generating' : '';

  return (
    <div
      onClick={handleClick}
      className={`focus-aura-container ${areaClass} ${activeClass} ${generatingClass} ${className}`}
    >
      {children}
    </div>
  );
};
