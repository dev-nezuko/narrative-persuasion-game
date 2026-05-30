// API utility for communicating with the Doorman Game backend

const API_BASE = 'http://127.0.0.1:8000';

/**
 * Send a chat message and get the doorman's response
 */
export async function sendMessage(sessionId, message, enableTts = true) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
      enable_tts: enableTts,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send message');
  }

  return response.json();
}

/**
 * Get session state (for restoring on page load)
 */
export async function getSession(sessionId) {
  const response = await fetch(`${API_BASE}/session/${sessionId}`);
  
  if (!response.ok) {
    throw new Error('Failed to get session');
  }

  return response.json();
}

/**
 * Reset a session to start fresh
 */
export async function resetSession(sessionId) {
  const response = await fetch(`${API_BASE}/session/reset?session_id=${sessionId}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to reset session');
  }

  return response.json();
}

/**
 * Generate a unique session ID
 */
export function generateSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

