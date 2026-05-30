import './MessageBubble.css';

export function MessageBubble({ message }) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`message-bubble ${isUser ? 'user' : 'doorman'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🚪'}
      </div>
      <div className="message-content">
        <div className="message-sender">
          {isUser ? 'You' : 'Marcus'}
        </div>
        <div className="message-text">
          {message.content}
        </div>
      </div>
    </div>
  );
}

