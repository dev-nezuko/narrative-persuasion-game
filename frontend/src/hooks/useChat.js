import { useState, useEffect, useCallback, useRef } from 'react';
import { sendMessage, getSession, resetSession, generateSessionId } from '../utils/api';

const SESSION_KEY = 'doorman_session_id';

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [gameState, setGameState] = useState({
    cumulativeScore: 0,
    threshold: 100,
    accessGranted: false,
    messageCount: 0,
  });
  const [lastScore, setLastScore] = useState(null);
  const [audioData, setAudioData] = useState(null);
  const [ttsEnabled, setTtsEnabled] = useState(true);

  // Initialize session on mount
  useEffect(() => {
    const initSession = async () => {
      // Try to restore existing session
      let storedSessionId = localStorage.getItem(SESSION_KEY);
      
      if (storedSessionId) {
        try {
          const session = await getSession(storedSessionId);
          setSessionId(storedSessionId);
          setGameState({
            cumulativeScore: session.cumulative_score,
            threshold: session.threshold,
            accessGranted: session.access_granted,
            messageCount: session.message_count,
          });
          
          // Restore message history
          if (session.history && session.history.length > 0) {
            const restoredMessages = session.history.map((msg, idx) => ({
              id: idx,
              role: msg.role,
              content: msg.content,
            }));
            setMessages(restoredMessages);
          }
        } catch (e) {
          // Session doesn't exist, create new one
          storedSessionId = generateSessionId();
          localStorage.setItem(SESSION_KEY, storedSessionId);
          setSessionId(storedSessionId);
        }
      } else {
        // Create new session
        storedSessionId = generateSessionId();
        localStorage.setItem(SESSION_KEY, storedSessionId);
        setSessionId(storedSessionId);
      }
    };

    initSession();
  }, []);

  // Send a message
  const send = useCallback(async (text) => {
    if (!sessionId || !text.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    setLastScore(null);

    // Add user message immediately
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: text.trim(),
    };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await sendMessage(sessionId, text.trim(), ttsEnabled);

      // Add doorman response
      const doormanMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.reply,
      };
      setMessages(prev => [...prev, doormanMessage]);

      // Update game state
      setGameState({
        cumulativeScore: response.cumulative_score,
        threshold: response.threshold,
        accessGranted: response.access_granted,
        messageCount: response.message_count,
      });

      // Set score delta for popup
      setLastScore({
        delta: response.score_delta,
        reasoning: response.reasoning,
      });

      // Set audio data if available
      if (response.audio_base64) {
        setAudioData(response.audio_base64);
      }

    } catch (e) {
      setError(e.message);
      // Remove the user message if failed
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, isLoading, ttsEnabled]);

  // Reset the game
  const reset = useCallback(async () => {
    if (!sessionId) return;

    try {
      await resetSession(sessionId);
      
      // Generate new session
      const newSessionId = generateSessionId();
      localStorage.setItem(SESSION_KEY, newSessionId);
      setSessionId(newSessionId);
      
      // Reset state
      setMessages([]);
      setGameState({
        cumulativeScore: 0,
        threshold: 100,
        accessGranted: false,
        messageCount: 0,
      });
      setLastScore(null);
      setAudioData(null);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }, [sessionId]);

  // Clear last score (after animation)
  const clearLastScore = useCallback(() => {
    setLastScore(null);
  }, []);

  // Clear audio data (after playing)
  const clearAudio = useCallback(() => {
    setAudioData(null);
  }, []);

  // Toggle TTS
  const toggleTts = useCallback(() => {
    setTtsEnabled(prev => !prev);
  }, []);

  return {
    messages,
    isLoading,
    error,
    gameState,
    lastScore,
    audioData,
    ttsEnabled,
    send,
    reset,
    clearLastScore,
    clearAudio,
    toggleTts,
  };
}

