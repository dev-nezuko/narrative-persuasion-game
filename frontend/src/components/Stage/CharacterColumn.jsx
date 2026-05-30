import { SpeechBubble } from '../SpeechBubble/SpeechBubble';
import './CharacterColumn.css';

export function CharacterColumn({ 
  type, // 'player' or 'doorman'
  message,
  isLoading 
}) {
  const isPlayer = type === 'player';
  
  return (
    <div className="character-column">
      {/* Speech Bubble */}
      <div className="bubble-container">
        {/* Show typing indicator OR message, not both */}
        {isLoading && !isPlayer ? (
          <div className="typing-bubble">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        ) : message ? (
          <SpeechBubble 
            key={message} 
            text={message} 
            direction={isPlayer ? 'left' : 'right'} 
          />
        ) : null}
      </div>
      
      {/* Character Avatar */}
      <div className="character-avatar-container">
        <div className={`character-glow ${isPlayer ? 'cyan' : 'purple'}`} />
        <div className="character-wrapper">
          {isPlayer ? <PlayerAvatar /> : <DoormanAvatar />}
          <p className={`character-name ${isPlayer ? 'cyan' : 'purple'}`}>
            {isPlayer ? 'YOU' : 'THE DOORMAN'}
          </p>
        </div>
      </div>
    </div>
  );
}

function PlayerAvatar() {
  return (
    <svg viewBox="0 0 200 350" className="character-svg">
      <defs>
        <linearGradient id="jacket" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{ stopColor: '#2a1a4a' }} />
          <stop offset="100%" style={{ stopColor: '#1a0a2e' }} />
        </linearGradient>
      </defs>
      {/* Head */}
      <ellipse cx="100" cy="60" rx="45" ry="55" fill="#e8d4c4" />
      {/* Jacket */}
      <path d="M55 100 Q50 150 60 200 L80 200 L80 130 Q100 140 120 130 L120 200 L140 200 Q150 150 145 100 Q120 120 100 115 Q80 120 55 100" fill="url(#jacket)" />
      {/* Shirt */}
      <path d="M80 130 L80 200 L120 200 L120 130 Q100 145 80 130" fill="#f5f5f5" />
      {/* Pants */}
      <path d="M60 200 L70 340 L90 340 L95 200" fill="#1a1a2e" />
      <path d="M105 200 L110 340 L130 340 L140 200" fill="#1a1a2e" />
      {/* Hair */}
      <ellipse cx="100" cy="50" rx="35" ry="12" fill="#4a3728" />
      <path d="M70 45 Q100 20 130 45" stroke="#4a3728" strokeWidth="8" fill="none" />
      {/* Eyes */}
      <circle cx="85" cy="55" r="4" fill="#2d5a7b" />
      <circle cx="115" cy="55" r="4" fill="#2d5a7b" />
      {/* Mouth */}
      <path d="M90 75 Q100 82 110 75" stroke="#c4a07a" strokeWidth="2" fill="none" />
    </svg>
  );
}

function DoormanAvatar() {
  return (
    <svg viewBox="0 0 200 350" className="character-svg doorman">
      <defs>
        <linearGradient id="suit" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{ stopColor: '#1a2a4a' }} />
          <stop offset="100%" style={{ stopColor: '#0a1525' }} />
        </linearGradient>
      </defs>
      {/* Head */}
      <ellipse cx="100" cy="60" rx="42" ry="52" fill="#d4b896" />
      {/* Suit */}
      <path d="M50 95 L45 200 L75 200 L80 140 L100 150 L120 140 L125 200 L155 200 L150 95 Q125 115 100 110 Q75 115 50 95" fill="url(#suit)" />
      {/* Shirt */}
      <path d="M80 140 L100 155 L120 140 L120 200 L80 200 Z" fill="#f0f0f0" />
      {/* Tie */}
      <path d="M100 155 L100 180" stroke="#1a1a2e" strokeWidth="3" />
      {/* Pants */}
      <path d="M45 200 L55 340 L80 340 L85 200" fill="#1a1a2e" />
      <path d="M115 200 L120 340 L145 340 L155 200" fill="#1a1a2e" />
      {/* Pocket Square */}
      <rect x="120" y="160" width="35" height="25" rx="2" fill="#e8e8e8" transform="rotate(5 137 172)" />
      {/* Hair */}
      <ellipse cx="100" cy="42" rx="38" ry="10" fill="#2a2a2a" />
      <path d="M65 35 Q100 15 135 35" stroke="#2a2a2a" strokeWidth="10" fill="none" />
      {/* Stern eyebrows */}
      <rect x="78" y="50" width="12" height="6" fill="#2a2a2a" />
      <rect x="110" y="50" width="12" height="6" fill="#2a2a2a" />
      {/* Stern mouth */}
      <path d="M85 80 L95 78 L105 78 L115 80" stroke="#a08060" strokeWidth="2" fill="none" />
    </svg>
  );
}

