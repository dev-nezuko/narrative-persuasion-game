import { useState, useEffect, useCallback, useRef } from 'react';
import { sendMessage, getSession, createSession, resetSession } from '../utils/api';

const SESSION_KEY = 'doorman_session_id';
const emptyState = { cumulativeScore: 0, threshold: 100, accessGranted: false, messageCount: 0 };

function storedSession() {
  try {
    const id = localStorage.getItem(SESSION_KEY);
    if (/^[A-Za-z0-9_-]{16,128}$/.test(id || '')) return id;
  } catch { /* Storage is optional. */ }
  return null;
}

function persist(id) {
  try { localStorage.setItem(SESSION_KEY, id); } catch { /* Keep playing in memory. */ }
}

// Resume the stored game if the server still has it; otherwise ask the server for a fresh ID.
async function restoreOrCreate(id) {
  if (id) {
    try { return await getSession(id); } catch (error) { if (error.status !== 404) throw error; }
  }
  return createSession();
}

function gameStateFrom(data) {
  return { cumulativeScore: data.cumulative_score, threshold: data.threshold, accessGranted: data.access_granted, messageCount: data.message_count };
}

export function useChat() {
  const [sessionId, setSessionId] = useState(null);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const [isRestoring, setIsRestoring] = useState(true);
  const [restoreFailed, setRestoreFailed] = useState(false);
  const [messages, setMessages] = useState([]);
  const [gameState, setGameState] = useState(emptyState);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [lastScore, setLastScore] = useState(null);
  const [audioData, setAudioData] = useState(null);
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const busy = useRef(false);

  useEffect(() => {
    let active = true;
    restoreOrCreate(storedSession()).then(session => {
      if (!active) return;
      persist(session.session_id);
      setSessionId(session.session_id);
      setGameState(gameStateFrom(session));
      setMessages((session.history || []).map((message, index) => ({ id: index, role: message.role, content: message.content })));
      setRestoreFailed(false);
      setError(null);
    }).catch(() => {
      if (!active) return;
      setRestoreFailed(true);
      setError('Could not reach the game server. Check that the backend is running.');
    }).finally(() => { if (active) setIsRestoring(false); });
    return () => { active = false; };
  }, [restoreAttempt]);

  const retryRestore = useCallback(() => {
    setIsRestoring(true);
    setRestoreAttempt(attempt => attempt + 1);
  }, []);

  const isLoading = isRestoring || isSending;

  const send = useCallback(async text => {
    const message = text.trim();
    if (busy.current || isLoading || !sessionId || !message) return false;
    busy.current = true; setIsSending(true); setError(null); setLastScore(null); setAudioData(null);
    const id = crypto.randomUUID();
    setMessages(previous => [...previous, { id, role: 'user', content: message }]);
    try {
      const response = await sendMessage(sessionId, message, ttsEnabled);
      if (typeof response.reply !== 'string' || !Number.isFinite(response.cumulative_score)) throw new Error('The game returned an invalid response.');
      setMessages(previous => [...previous, { id: crypto.randomUUID(), role: 'assistant', content: response.reply }]);
      setGameState(gameStateFrom(response)); setLastScore({ delta: response.score_delta }); setAudioData(response.audio_base64 || null);
      return true;
    } catch (failure) {
      setError(failure.message);
      setMessages(previous => previous.filter(entry => entry.id !== id));
      return false;
    } finally {
      busy.current = false; setIsSending(false);
    }
  }, [sessionId, isLoading, ttsEnabled]);

  const reset = useCallback(async () => {
    if (busy.current || isLoading || !sessionId) return;
    busy.current = true; setIsSending(true);
    try {
      const session = await resetSession(sessionId);
      setMessages([]); setGameState({ ...emptyState, cumulativeScore: session.cumulative_score }); setLastScore(null); setAudioData(null); setError(null);
    } catch (failure) {
      setError(failure.message);
    } finally {
      busy.current = false; setIsSending(false);
    }
  }, [sessionId, isLoading]);

  const clearLastScore = useCallback(() => setLastScore(null), []);
  const clearAudio = useCallback(() => setAudioData(null), []);
  const toggleTts = useCallback(() => setTtsEnabled(previous => !previous), []);

  return { messages, isLoading, isRestoring, error, restoreFailed, gameState, lastScore, audioData, ttsEnabled, send, reset, retryRestore, clearLastScore, clearAudio, toggleTts };
}
