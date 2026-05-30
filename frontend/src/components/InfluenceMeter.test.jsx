import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { InfluenceMeter } from './InfluenceMeter';

describe('InfluenceMeter', () => {
  it('reports progress towards the threshold', () => {
    render(<InfluenceMeter score={40} threshold={100} accessGranted={false} />);
    const meter = screen.getByRole('progressbar', { name: /influence/i });
    expect(meter).toHaveAttribute('aria-valuenow', '40');
    expect(meter).toHaveTextContent('40%');
  });

  it('never shows a negative fill', () => {
    render(<InfluenceMeter score={-30} threshold={100} accessGranted={false} />);
    expect(screen.getByRole('progressbar')).toHaveTextContent('0%');
  });

  it('announces a win', () => {
    render(<InfluenceMeter score={112} threshold={100} accessGranted />);
    expect(screen.getByRole('progressbar')).toHaveTextContent(/access granted/i);
  });
});
