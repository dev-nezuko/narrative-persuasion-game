const API_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/, '');

export class ApiError extends Error {
 constructor(message, status) { super(message); this.name = 'ApiError'; this.status = status; }
}

async function request(path, options = {}, timeout = 155000) {
 const controller = new AbortController();
 const timer = setTimeout(() => controller.abort(), timeout);
 try {
  const response = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
  if (response.status === 429) throw new ApiError('Marcus needs a moment. Wait a few seconds and try again.', 429);
  if (!response.ok) throw new ApiError('The game service could not complete this request. Please try again.', response.status);
  return await response.json();
 } catch (error) {
  if (error.name === 'AbortError') throw new ApiError('The game request timed out. Try again later.', 0);
  throw error;
 } finally { clearTimeout(timer); }
}
export function sendMessage(sessionId, message, enableTts = false) {
 return request('/chat', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({session_id:sessionId,message,enable_tts:enableTts}) });
}
export function createSession() { return request('/session', {method:'POST'}, 10000); }
export function getSession(sessionId) { return request(`/session/${encodeURIComponent(sessionId)}`, {}, 10000); }
export function resetSession(sessionId) { return request(`/session/reset?session_id=${encodeURIComponent(sessionId)}`, {method:'POST'}, 10000); }
