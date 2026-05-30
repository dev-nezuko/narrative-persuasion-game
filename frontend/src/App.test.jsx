import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import { installFakeServer } from './test/fakeServer';

const input = () => screen.getByLabelText(/your message/i);

describe('App', () => {
  it('replaces a stale stored session with a server-issued one', async () => {
    localStorage.setItem('doorman_session_id', 'stale-session-id-0000');
    const { fetchMock } = installFakeServer();
    render(<App />);
    await waitFor(() => expect(input()).toBeEnabled());
    expect(localStorage.getItem('doorman_session_id')).toBe('server-issued-id-0001');
    expect(fetchMock.mock.calls.map(([url, o = {}]) => `${o.method || 'GET'} ${new URL(url).pathname}`).slice(0, 2))
      .toEqual(['GET /session/stale-session-id-0000', 'POST /session']);
  });

  it('plays a turn and shows the reply and new score', async () => {
    installFakeServer({ chat: () => ({ status: 200, delta: 20, reply: 'Jazz, huh? Keep talking.' }) });
    render(<App />);
    await waitFor(() => expect(input()).toBeEnabled());
    await userEvent.type(input(), 'I used to play sax{enter}');
    expect(await screen.findByText('Jazz, huh? Keep talking.')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '20');
    expect(input()).toHaveValue('');
  });

  it('shows an error and keeps the draft when a turn fails', async () => {
    installFakeServer({ chat: () => ({ status: 429 }) });
    render(<App />);
    await waitFor(() => expect(input()).toBeEnabled());
    await userEvent.type(input(), 'Let me in{enter}');
    expect(await screen.findByRole('alert')).toHaveTextContent(/Marcus needs a moment/);
    expect(input()).toHaveValue('Let me in');
  });

  it('shows the victory screen at the threshold and can start over', async () => {
    installFakeServer({ chat: () => ({ status: 200, delta: 100, reply: 'Head on in, friend.' }) });
    render(<App />);
    await waitFor(() => expect(input()).toBeEnabled());
    await userEvent.type(input(), 'Coltrane{enter}');
    const again = await screen.findByRole('button', { name: /play again/i });
    await userEvent.click(again);
    await waitFor(() => expect(screen.queryByRole('button', { name: /play again/i })).not.toBeInTheDocument());
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '0');
  });

  it('opens with Marcus speaking first and a hint for new players', async () => {
    installFakeServer();
    render(<App />);
    expect(await screen.findByText(/Give me one good reason/)).toBeInTheDocument();
    expect(screen.getByText(/Find out what he cares about/)).toBeInTheDocument();
  });

  it('offers a retry when the server cannot be reached, then recovers', async () => {
    const offline = vi.fn(() => Promise.reject(new TypeError('Failed to fetch')));
    vi.stubGlobal('fetch', offline);
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not reach the game server/);
    expect(input()).toBeDisabled();
    installFakeServer();
    await userEvent.click(screen.getByRole('button', { name: /try again/i }));
    await waitFor(() => expect(input()).toBeEnabled());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('moves focus to Play again when access is granted', async () => {
    installFakeServer({ chat: () => ({ status: 200, delta: 100, reply: 'Head on in, friend.' }) });
    render(<App />);
    await waitFor(() => expect(input()).toBeEnabled());
    await userEvent.type(input(), 'Coltrane{enter}');
    expect(await screen.findByRole('button', { name: /play again/i })).toHaveFocus();
    expect(screen.getByRole('dialog', { name: /access granted/i })).toBeInTheDocument();
  });

  it('still plays on plain-HTTP origins where crypto.randomUUID is missing', async () => {
    vi.stubGlobal('crypto', { ...globalThis.crypto, randomUUID: undefined });
    installFakeServer({ chat: () => ({ status: 200, delta: 10, reply: 'Go on.' }) });
    render(<App />);
    await waitFor(() => expect(input()).toBeEnabled());
    await userEvent.type(input(), 'Evening{enter}');
    expect(await screen.findByText('Go on.')).toBeInTheDocument();
    expect(input()).toBeEnabled();
  });
});
