import './SpeechBubble.css';

export function SpeechBubble({ text, direction = 'left' }) {
  return (
    <div className={`speech-bubble ${direction}`}>
      <span className="speech-text">{text}</span>
    </div>
  );
}

