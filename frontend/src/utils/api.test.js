import { describe, expect, it, vi } from 'vitest';
import { ApiError, createSession, getSession, sendMessage } from './api';

const respond = (status, body = {}) => vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status }))));

describe('api client', () => {
  it('asks the server to create sessions', async () => {
    respond(201, { session_id: 'server-issued-id-0001' });
    await expect(createSession()).resolves.toEqual({ session_id: 'server-issued-id-0001' });
    expect(fetch).toHaveBeenCalledWith('http://127.0.0.1:8000/session', expect.objectContaining({ method: 'POST' }));
  });

  it('keeps the HTTP status on failures so callers can tell a missing session apart', async () => {
    respond(404);
    const error = await getSession('server-issued-id-0001').catch(e => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(404);
  });

  it('explains rate limiting in game terms', async () => {
    respond(429);
    await expect(sendMessage('server-issued-id-0001', 'hi')).rejects.toThrow(/Marcus needs a moment/);
  });

  it('turns an aborted request into a timeout message', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(Object.assign(new Error('aborted'), { name: 'AbortError' }))));
    await expect(sendMessage('server-issued-id-0001', 'hi')).rejects.toThrow(/timed out/);
  });
});
