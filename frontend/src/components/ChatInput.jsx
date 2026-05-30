import { useState } from 'react';
import './ChatInput.css';

export function ChatInput({ onSend, isLoading, disabled }) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <input
        type="text"
        className="chat-input"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder={disabled ? "You're in! Enjoy the party 🎉" : "What do you say to the doorman?"}
        disabled={isLoading || disabled}
        autoComplete="off"
      />
      <button 
        type="submit" 
        className="send-button"
        disabled={isLoading || disabled || !message.trim()}
      >
        {isLoading ? (
          <span className="loading-dots">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </span>
        ) : (
          <span className="send-icon">➤</span>
        )}
      </button>
    </form>
  );
}
