import { useState } from 'react';
import { SendIcon } from './Icons';
import './ChatInput.css';

export function ChatInput({ onSend, isLoading, disabled }) {
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      if (await onSend(message.trim())) setMessage('');
    }
  };

  return (
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <input
        type="text"
        aria-label="Your message to the doorman"
        maxLength={2000}
        className="chat-input"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder={disabled ? "You're in. Enjoy the night." : "What do you say to Marcus?"}
        disabled={isLoading || disabled}
        autoComplete="off"
      />
      <button
        type="submit"
        aria-label={isLoading ? 'Waiting for the doorman' : 'Send message'}
        className="send-button"
        disabled={isLoading || disabled || !message.trim()}
      >
        {isLoading ? (
          <span className="loading-dots" aria-hidden="true">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </span>
        ) : (
          <SendIcon className="send-icon" />
        )}
      </button>
    </form>
  );
}
