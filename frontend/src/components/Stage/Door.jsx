import { useEffect, useState } from 'react';
import './Door.css';

export function Door({ isOpen }) {
  const [showInterior, setShowInterior] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // Delay showing interior until doors start opening
      const timer = setTimeout(() => setShowInterior(true), 500);
      return () => clearTimeout(timer);
    } else {
      // Hide interior when doors close
      setShowInterior(false);
    }
  }, [isOpen]);

  return (
    <div className="door-container">
      {/* Door Frame */}
      <div className="door-frame">
        {/* Club Interior (revealed when doors open) */}
        <div className={`club-interior ${showInterior ? 'visible' : ''}`}>
          {/* Stage Lights */}
          <div className="lights-container">
            <div className="light-beam pink" style={{ left: '20%', transform: 'rotate(15deg)' }} />
            <div className="light-beam cyan" style={{ left: '35%', transform: 'rotate(-10deg)', animationDelay: '0.1s' }} />
            <div className="light-beam green" style={{ left: '50%', animationDelay: '0.2s' }} />
            <div className="light-beam yellow" style={{ left: '65%', transform: 'rotate(10deg)', animationDelay: '0.15s' }} />
            <div className="light-beam purple" style={{ left: '80%', transform: 'rotate(-15deg)', animationDelay: '0.25s' }} />
          </div>
          
          {/* Dancing Silhouettes */}
          <div className="silhouettes">
            <div className="silhouette" style={{ width: '32px', height: '80px', animationDuration: '0.5s' }} />
            <div className="silhouette" style={{ width: '40px', height: '96px', animationDuration: '0.6s', animationDelay: '0.1s' }} />
            <div className="silhouette" style={{ width: '32px', height: '72px', animationDuration: '0.45s', animationDelay: '0.2s' }} />
            <div className="silhouette" style={{ width: '48px', height: '104px', animationDuration: '0.55s', animationDelay: '0.15s' }} />
            <div className="silhouette" style={{ width: '32px', height: '80px', animationDuration: '0.5s', animationDelay: '0.25s' }} />
          </div>
        </div>

        {/* Door Leaves */}
        <div className="doors">
          <div className={`door-leaf left ${isOpen ? 'open' : ''}`}>
            <div className="door-decoration">
              <div className="door-decoration-inner" />
            </div>
          </div>
          <div className={`door-leaf right ${isOpen ? 'open' : ''}`}>
            <div className="door-decoration">
              <div className="door-decoration-inner" />
            </div>
          </div>
        </div>

        {/* Neon frame glow */}
        <div className="door-glow" />
      </div>

      {/* Velvet Rope */}
      <div className="velvet-rope">
        <div className="rope-post" />
        <div className="rope" />
        <div className="rope-post" />
      </div>
    </div>
  );
}

