import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  it('only enables sending once there is text', async () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} disabled={false} />);
    const send = screen.getByRole('button', { name: /send/i });
    expect(send).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/your message/i), 'Evening');
    expect(send).toBeEnabled();
  });

  it('clears the draft after a successful send and keeps it after a failure', async () => {
    const onSend = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    render(<ChatInput onSend={onSend} isLoading={false} disabled={false} />);
    const input = screen.getByLabelText(/your message/i);
    await userEvent.type(input, '  Evening, Marcus  {enter}');
    expect(onSend).toHaveBeenCalledWith('Evening, Marcus');
    expect(input).toHaveValue('  Evening, Marcus  ');
    await userEvent.type(input, '{enter}');
    expect(input).toHaveValue('');
  });

  it('caps input at the server limit', () => {
    render(<ChatInput onSend={vi.fn()} isLoading={false} disabled={false} />);
    expect(screen.getByLabelText(/your message/i)).toHaveAttribute('maxLength', '2000');
  });
});
