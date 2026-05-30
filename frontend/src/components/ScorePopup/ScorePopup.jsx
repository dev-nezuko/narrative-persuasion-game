import { useEffect, useState } from 'react';
import './ScorePopup.css';

export function ScorePopup({ score, onComplete }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      onComplete?.();
    }, 2000);
    
    return () => clearTimeout(timer);
  }, [score, onComplete]);

  if (!visible) return null;

  const isPositive = score >= 0;
  
  return (
    <div className="score-popup-overlay">
      <div className={`score-popup ${isPositive ? 'positive' : 'negative'}`}>
        {isPositive ? '+' : ''}{score}
      </div>
    </div>
  );
}

