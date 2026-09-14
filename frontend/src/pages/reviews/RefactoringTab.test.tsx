import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { RefactoringTab } from './RefactoringTab';
import { RefactoringFinding } from '../../api/reviews';

const mockFindings: RefactoringFinding[] = [
  {
    refactoring_type: 'Extract Method',
    priority: 'high',
    category: 'complexity',
    file_path: 'src/main.py',
    line_number: 42,
    explanation: 'Function process_data is too long and complex. Extract helper method.',
    current_problem: 'High nesting in process_data',
    suggested_refactoring: 'Extract inner loop into separate function',
    before_preview: 'def process_data():\n    # 50 lines of logic',
    after_preview: 'def process_data():\n    step1()\n    step2()',
    benefits: ['Reduced cyclomatic complexity', 'Improved testability'],
    risks: ['Minor indirection'],
    estimated_effort_hours: 2.0,
    confidence_score: 0.95,
  },
  {
    refactoring_type: 'Remove Duplicate Code',
    priority: 'medium',
    category: 'duplication',
    file_path: 'src/utils.py',
    line_number: 10,
    explanation: 'Duplicate validation logic found across three files.',
    current_problem: 'Repeated user validation code',
    suggested_refactoring: 'Create shared helper validate_user()',
    before_preview: 'if not user or not user.is_active:\n    raise Error()',
    after_preview: 'validate_active_user(user)',
    benefits: ['Single source of truth', 'Easier maintenance'],
    risks: ['Ensuring callers are updated'],
    estimated_effort_hours: 1.0,
    confidence_score: 0.88,
  },
];

describe('RefactoringTab Component', () => {
  it('renders summary cards with maintainability score, tech debt reduction, and total count', () => {
    render(
      <RefactoringTab
        findings={mockFindings}
        overallPriority="high"
        estimatedEffort={3.0}
        estimatedMaintainabilityImprovement={25.0}
        estimatedTechnicalDebtReduction={4.5}
        estimatedComplexityReduction={30.0}
      />
    );

    expect(screen.getByText('+25%')).toBeInTheDocument();
    expect(screen.getByText('3.0h')).toBeInTheDocument();
    expect(screen.getByText('-4.5h')).toBeInTheDocument();
    expect(screen.getByText('-30%')).toBeInTheDocument();
    expect(screen.getAllByText('2').length).toBeGreaterThanOrEqual(1); // Suggestions count card
  });

  it('filters findings by search query', () => {
    render(
      <RefactoringTab
        findings={mockFindings}
        overallPriority="high"
        estimatedEffort={3.0}
        estimatedMaintainabilityImprovement={25.0}
        estimatedTechnicalDebtReduction={4.5}
        estimatedComplexityReduction={30.0}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search suggestions…');
    fireEvent.change(searchInput, { target: { value: 'Duplicate' } });

    expect(screen.getByText('[Remove Duplicate Code]')).toBeInTheDocument();
    expect(screen.queryByText('[Extract Method]')).not.toBeInTheDocument();
  });

  it('expands finding details when clicked', () => {
    render(
      <RefactoringTab
        findings={mockFindings}
        overallPriority="high"
        estimatedEffort={3.0}
        estimatedMaintainabilityImprovement={25.0}
        estimatedTechnicalDebtReduction={4.5}
        estimatedComplexityReduction={30.0}
      />
    );

    const button = screen.getByText(/\[Extract Method\]/);
    fireEvent.click(button);

    expect(screen.getByText('Reduced cyclomatic complexity')).toBeInTheDocument();
    expect(screen.getByText('Current Problem')).toBeInTheDocument();
    expect(screen.getByText('Suggested Refactoring')).toBeInTheDocument();
  });

  it('renders empty state when no findings are passed', () => {
    render(
      <RefactoringTab
        findings={[]}
        overallPriority={null}
        estimatedEffort={0}
        estimatedMaintainabilityImprovement={0}
      />
    );

    expect(screen.getByTestId('category-passed-refactoring')).toBeInTheDocument();
    expect(screen.getByText(/Refactoring Analysis Passed/i)).toBeInTheDocument();
  });
});
