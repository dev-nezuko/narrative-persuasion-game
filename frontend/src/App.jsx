import { useChat } from './hooks/useChat';
import { Stage } from './components/Stage';
import { InfluenceMeter } from './components/InfluenceMeter';
import { ChatInput } from './components/ChatInput';
import { VictoryScreen } from './components/VictoryScreen';
import { ScorePopup } from './components/ScorePopup';
import { AudioPlayer } from './components/AudioPlayer';
import { RestartIcon, VoiceOffIcon, VoiceOnIcon } from './components/Icons';
import './App.css';

const OPENING_LINE = "Line's long tonight. Give me one good reason you belong inside.";

function App() {
  const {
    messages,
    isLoading,
    isRestoring,
    error,
    restoreFailed,
    gameState,
    lastScore,
    audioData,
    ttsEnabled,
    send,
    reset,
    retryRestore,
    clearLastScore,
    clearAudio,
    toggleTts,
  } = useChat();

  const latestPlayerMessage = messages.findLast(m => m.role === 'user')?.content || '';
  const latestDoormanMessage = messages.findLast(m => m.role === 'assistant')?.content
    || (isRestoring || restoreFailed ? '' : OPENING_LINE);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <h1 className="app-title">The Doorman</h1>
          <p className="app-subtitle">A persuasion game at a fictional club</p>
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
            type="button"
            className={`icon-btn ${ttsEnabled ? 'active' : ''}`}
            onClick={toggleTts}
            aria-label={ttsEnabled ? 'Turn voice off' : 'Turn voice on'}
            aria-pressed={ttsEnabled}
            title={ttsEnabled ? 'Turn voice off' : 'Turn voice on (needs a live provider)'}
          >
            {ttsEnabled ? <VoiceOnIcon /> : <VoiceOffIcon />}
          </button>
          <button type="button" className="icon-btn" onClick={reset} disabled={isLoading} aria-label="Start over" title="Start over">
            <RestartIcon />
          </button>
        </div>
      </header>

      <main className="app-main">
        <Stage
          playerMessage={latestPlayerMessage}
          doormanMessage={latestDoormanMessage}
          isLoading={isLoading}
          isOpen={gameState.accessGranted}
        />
      </main>

      {error && (
        <div className="error-banner" role="alert">
          <span>{error}</span>
          {restoreFailed && <button type="button" onClick={retryRestore}>Try again</button>}
        </div>
      )}

      <footer className="app-footer">
        {messages.length === 0 && !isRestoring && !restoreFailed && (
          <p className="game-hint">Marcus decides who gets in. Find out what he cares about.</p>
        )}
        <ChatInput
          onSend={send}
          isLoading={isLoading}
          disabled={gameState.accessGranted || restoreFailed}
        />
      </footer>

      {lastScore && (
        <ScorePopup
          score={lastScore.delta}
          onComplete={clearLastScore}
        />
      )}

      <AudioPlayer
        audioBase64={audioData}
        onFinished={clearAudio}
      />

      {gameState.accessGranted && (
        <VictoryScreen onPlayAgain={reset} />
      )}
    </div>
  );
}

export default App;
