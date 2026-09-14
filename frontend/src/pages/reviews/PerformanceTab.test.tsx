import React from 'react';
import { render, screen } from '@testing-library/react';
import { PerformanceTab } from './PerformanceTab';
import { describe, it, expect } from 'vitest';

const mockFindings = [
  {
    issue: 'High CPU Usage',
    severity: 'high' as const,
    confidence_score: 0.9,
    file_path: 'src/main.ts',
  },
];

const mockRecommendations = [
  {
    title: 'Optimize Loop',
    description: 'Use map instead of forEach',
  },
];

describe('PerformanceTab', () => {
  it('renders correctly with findings', () => {
    render(
      <PerformanceTab
        findings={mockFindings}
        recommendations={mockRecommendations}
        performanceScore={85}
        estimatedCpuSavings={15}
        estimatedMemorySavings={10}
        estimatedLatencyImprovement={5}
      />
    );
    
    expect(screen.getByText('Performance Score')).toBeInTheDocument();
    expect(screen.getByText('Good')).toBeInTheDocument();
    expect(screen.getByText('High CPU Usage')).toBeInTheDocument();
    expect(screen.getByText('Optimize Loop')).toBeInTheDocument();
  });
  
  it('renders empty state correctly', () => {
    render(
      <PerformanceTab
        findings={[]}
        recommendations={[]}
        performanceScore={100}
        estimatedCpuSavings={0}
        estimatedMemorySavings={0}
        estimatedLatencyImprovement={0}
      />
    );
    
    expect(screen.getByTestId('category-passed-performance')).toBeInTheDocument();
    expect(screen.getByText(/Performance Analysis Passed/i)).toBeInTheDocument();
  });
});
