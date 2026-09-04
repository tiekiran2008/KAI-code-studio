import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ArchitectureTab } from './ArchitectureTab';
import { ArchitectureFinding } from '../../api/reviews';

const sampleFindings: ArchitectureFinding[] = [
  {
    category: 'clean_architecture',
    severity: 'high',
    priority: 'high',
    file_path: 'src/domain/user.py',
    line_number: 15,
    explanation: 'Domain entity directly imports ORM model.',
    root_cause: 'Coupling domain to persistence layer.',
    business_impact: 'High friction when modifying database schema.',
    recommendation: 'Decouple domain model using mapping interface.',
    estimated_effort_hours: 3.5,
    confidence_score: 0.95,
  },
  {
    category: 'complexity',
    severity: 'medium',
    priority: 'medium',
    file_path: 'src/services/order_service.py',
    line_number: 45,
    explanation: 'Order processing method has high cyclomatic complexity.',
    root_cause: 'Multiple nested if-else branches.',
    business_impact: 'Increased bug risk during maintenance.',
    recommendation: 'Extract sub-routines into strategy objects.',
    estimated_effort_hours: 2.0,
    confidence_score: 0.88,
  },
];

describe('ArchitectureTab Component', () => {
  it('renders overall health ring and 8 score indicators', () => {
    render(
      <ArchitectureTab
        findings={sampleFindings}
        overallHealthScore={85.0}
        architectureScore={88.0}
        maintainabilityScore={80.0}
        technicalDebtScore={78.0}
        complexityScore={82.0}
        documentationScore={85.0}
        modularityScore={84.0}
        testabilityScore={86.0}
      />
    );

    expect(screen.getAllByText('Overall Health').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Architecture').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Maintainability').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Tech Debt').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Complexity').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Documentation').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Modularity').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Testability').length).toBeGreaterThanOrEqual(1);

    expect(screen.getByText('Domain entity directly imports ORM model.')).toBeInTheDocument();
  });

  it('filters findings by search query', () => {
    render(<ArchitectureTab findings={sampleFindings} />);

    const searchInput = screen.getByPlaceholderText(/Search architecture & quality findings/i);
    fireEvent.change(searchInput, { target: { value: 'Order processing' } });

    expect(screen.getByText('Order processing method has high cyclomatic complexity.')).toBeInTheDocument();
    expect(screen.queryByText('Domain entity directly imports ORM model.')).not.toBeInTheDocument();
  });

  it('expands finding card to show root cause, business impact, and recommendation', () => {
    render(<ArchitectureTab findings={sampleFindings} />);

    const cardButton = screen.getByText('Domain entity directly imports ORM model.').closest('button');
    expect(cardButton).not.toBeNull();
    fireEvent.click(cardButton!);

    expect(screen.getByText('Coupling domain to persistence layer.')).toBeInTheDocument();
    expect(screen.getByText('High friction when modifying database schema.')).toBeInTheDocument();
    expect(screen.getByText('Decouple domain model using mapping interface.')).toBeInTheDocument();
  });

  it('renders empty state message when no findings are passed', () => {
    render(<ArchitectureTab findings={[]} />);
    expect(
      screen.getByText('No architecture or code quality issues found. Codebase maintains high architectural integrity!')
    ).toBeInTheDocument();
  });
});
