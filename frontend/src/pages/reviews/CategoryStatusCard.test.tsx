import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CategoryStatusCard, CategoryKey } from './CategoryStatusCard';
import type { CategoryAnalysisMetadata } from '../../api/reviews';

describe('CategoryStatusCard Component', () => {
  const allCategories: CategoryKey[] = [
    'code_quality',
    'security',
    'performance',
    'refactoring',
    'architecture',
  ];

  describe('SUCCESS_ZERO_FINDINGS state', () => {
    it.each(allCategories)('renders Analysis Passed card for %s with zero findings', (catKey) => {
      const metadata: CategoryAnalysisMetadata = {
        status: 'completed',
        findings_count: 0,
        evaluated_at: '2026-09-13T12:00:00Z',
      };

      render(
        <CategoryStatusCard
          categoryKey={catKey}
          reviewStatus="completed"
          metadata={metadata}
          findingsCount={0}
        />
      );

      // Verify the passed test id exists
      expect(screen.getByTestId(`category-passed-${catKey}`)).toBeInTheDocument();
      // Verify "Analysis Passed" text is displayed
      expect(screen.getByText(new RegExp(`Analysis Passed`, 'i'))).toBeInTheDocument();
      // Verify Total Findings is 0
      expect(screen.getByText('Total Findings')).toBeInTheDocument();
    });

    it('renders real metadata chips when backend provides them', () => {
      const metadata: CategoryAnalysisMetadata = {
        status: 'completed',
        findings_count: 0,
        files_analyzed: 14,
        duration_ms: 1250,
        evaluated_at: '2026-09-13T12:00:00Z',
      };

      render(
        <CategoryStatusCard
          categoryKey="security"
          reviewStatus="completed"
          metadata={metadata}
          findingsCount={0}
        />
      );

      expect(screen.getByText('Files analyzed')).toBeInTheDocument();
      expect(screen.getByText('14')).toBeInTheDocument();
      expect(screen.getByText('Duration')).toBeInTheDocument();
      expect(screen.getByText('1.3s')).toBeInTheDocument();
      expect(screen.getByText('Evaluated at')).toBeInTheDocument();
    });

    it('does NOT render fake/hardcoded metadata when not provided by backend', () => {
      const metadata: CategoryAnalysisMetadata = {
        status: 'completed',
        findings_count: 0,
      };

      render(
        <CategoryStatusCard
          categoryKey="code_quality"
          reviewStatus="completed"
          metadata={metadata}
          findingsCount={0}
        />
      );

      expect(screen.queryByText('Files analyzed')).not.toBeInTheDocument();
      expect(screen.queryByText('Duration')).not.toBeInTheDocument();
      expect(screen.queryByText('Evaluated at')).not.toBeInTheDocument();
    });
  });

  describe('SUCCESS_WITH_FINDINGS state', () => {
    it.each(allCategories)('renders compact findings header for %s when findings exist', (catKey) => {
      const metadata: CategoryAnalysisMetadata = {
        status: 'completed',
        findings_count: 3,
      };

      render(
        <CategoryStatusCard
          categoryKey={catKey}
          reviewStatus="completed"
          metadata={metadata}
          findingsCount={3}
          severityCounts={{
            critical: 1,
            high: 2,
            medium: 0,
            low: 0,
          }}
        />
      );

      expect(screen.getByTestId(`category-findings-header-${catKey}`)).toBeInTheDocument();
      expect(screen.getByText(/3 findings detected/i)).toBeInTheDocument();
      expect(screen.getByText('Critical')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
    });
  });

  describe('NOT_EVALUATED state', () => {
    it.each(allCategories)('renders Not Evaluated card for %s when disabled', (catKey) => {
      const metadata: CategoryAnalysisMetadata = {
        status: 'not_evaluated',
        findings_count: 0,
      };

      render(
        <CategoryStatusCard
          categoryKey={catKey}
          reviewStatus="completed"
          metadata={metadata}
          findingsCount={0}
        />
      );

      expect(screen.getByTestId(`category-not-evaluated-${catKey}`)).toBeInTheDocument();
      expect(screen.getByText('Not Evaluated')).toBeInTheDocument();
    });
  });

  describe('FAILED state', () => {
    it.each(allCategories)('renders Analysis Failed card for %s when category failed', (catKey) => {
      const metadata: CategoryAnalysisMetadata = {
        status: 'failed',
        findings_count: 0,
      };

      render(
        <CategoryStatusCard
          categoryKey={catKey}
          reviewStatus="completed"
          metadata={metadata}
          findingsCount={0}
        />
      );

      expect(screen.getByTestId(`category-failed-${catKey}`)).toBeInTheDocument();
      expect(screen.getByText('Analysis Failed')).toBeInTheDocument();
    });

    it('renders FAILED when overall review failed', () => {
      render(
        <CategoryStatusCard
          categoryKey="security"
          reviewStatus="failed"
          findingsCount={0}
        />
      );

      expect(screen.getByTestId('category-failed-security')).toBeInTheDocument();
      expect(screen.getByText('Analysis Failed')).toBeInTheDocument();
    });
  });

  describe('LOADING state', () => {
    it('renders loading spinner when review is in_progress', () => {
      render(
        <CategoryStatusCard
          categoryKey="security"
          reviewStatus="in_progress"
          findingsCount={0}
        />
      );

      expect(screen.getByText(/Analysing security/i)).toBeInTheDocument();
    });
  });
});
