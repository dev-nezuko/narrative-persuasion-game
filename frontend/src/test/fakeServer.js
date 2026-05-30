import { vi } from 'vitest';

// In-memory stand-in for the FastAPI routes the UI calls.
export function installFakeServer({ chat } = {}) {
  const sessions = new Map();
  let counter = 0;
  const json = (status, body) => Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
  const state = s => ({ session_id: s.id, cumulative_score: s.score, threshold: 100, access_granted: s.score >= 100, message_count: s.history.length / 2, history: s.history });

  const fetchMock = vi.fn((url, options = {}) => {
    const { pathname, searchParams } = new URL(url);
    const method = options.method || 'GET';
    if (method === 'POST' && pathname === '/session') {
      const s = { id: `server-issued-id-${String(++counter).padStart(4, '0')}`, score: 0, history: [] };
      sessions.set(s.id, s);
      return json(201, state(s));
    }
    if (method === 'GET' && pathname.startsWith('/session/')) {
      const s = sessions.get(decodeURIComponent(pathname.slice('/session/'.length)));
      return s ? json(200, state(s)) : json(404, { detail: 'Session not found or expired' });
    }
    if (method === 'POST' && pathname === '/session/reset') {
      const s = sessions.get(searchParams.get('session_id'));
      if (!s) return json(404, {});
      s.score = 0; s.history = [];
      return json(200, { status: 'ok', session_id: s.id, cumulative_score: 0 });
    }
    if (method === 'POST' && pathname === '/chat') {
      const body = JSON.parse(options.body);
      const s = sessions.get(body.session_id);
      if (!s) return json(404, {});
      const outcome = chat ? chat(body, s) : { status: 200, delta: 20, reply: 'Hmm. Go on.' };
      if (outcome.status !== 200) return json(outcome.status, { detail: 'nope' });
      s.score += outcome.delta;
      s.history.push({ role: 'user', content: body.message }, { role: 'assistant', content: outcome.reply });
      return json(200, { ...state(s), reply: outcome.reply, score_delta: outcome.delta, reasoning: 'Round scored by the game evaluator', audio_base64: null });
    }
    return json(404, {});
  });
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock, sessions };
}
