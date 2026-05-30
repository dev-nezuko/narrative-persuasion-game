import { useEffect } from 'react';
import { useChat } from './hooks/useChat';
import { Stage } from './components/Stage';
import { InfluenceMeter } from './components/InfluenceMeter';
import { ChatInput } from './components/ChatInput';
import { VictoryScreen } from './components/VictoryScreen';
import { ScorePopup } from './components/ScorePopup';
import { AudioPlayer } from './components/AudioPlayer';
import './App.css';

function App() {
  const {
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
  } = useChat();

  // Get the latest message from each participant
  const latestPlayerMessage = [...messages].reverse().find(m => m.role === 'user')?.content || '';
  const latestDoormanMessage = [...messages].reverse().find(m => m.role === 'assistant')?.content || '';

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">🎭 THE DOORMAN GAME</h1>
          <p className="app-subtitle">BLVD DUBAI</p>
        </div>
        <div className="header-center">
          <InfluenceMeter 
            score={gameState.cumulativeScore}
            threshold={gameState.threshold}
            accessGranted={gameState.accessGranted}
          />
        </div>
        <div className="header-right">
          <button 
            className={`icon-btn ${ttsEnabled ? 'active' : ''}`}
            onClick={toggleTts}
            title={ttsEnabled ? 'Mute voice' : 'Enable voice'}
          >
            {ttsEnabled ? '🔊' : '🔇'}
          </button>
          <button className="icon-btn" onClick={reset} title="Start over">
            ↺
          </button>
        </div>
      </header>

      {/* Main Stage */}
      <Stage 
        playerMessage={latestPlayerMessage}
        doormanMessage={latestDoormanMessage}
        isLoading={isLoading}
        isOpen={gameState.accessGranted}
      />

      {/* Error Display */}
      {error && (
        <div className="error-banner">
          ⚠️ {error}
        </div>
      )}

      {/* Chat Input */}
      <footer className="app-footer">
        <ChatInput 
          onSend={send}
          isLoading={isLoading}
          disabled={gameState.accessGranted}
        />
      </footer>

      {/* Score Popup */}
      {lastScore && (
        <ScorePopup 
          score={lastScore.delta} 
          onComplete={clearLastScore}
        />
      )}

      {/* Audio Player (hidden) */}
      <AudioPlayer 
        audioBase64={audioData}
        onFinished={clearAudio}
      />

      {/* Victory Overlay */}
      {gameState.accessGranted && (
        <VictoryScreen onPlayAgain={reset} />
      )}
    </div>
  );
}

export default App;
