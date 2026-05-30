import { useEffect, useRef } from 'react';
import './VictoryScreen.css';
import rickrollAudio from '../assets/audio/never-gonna-give-you-up-rickroll.mp3';

export function VictoryScreen({ onPlayAgain }) {
  const audioRef = useRef(null);

  useEffect(() => {
    // Play the rickroll when victory screen mounts
    if (audioRef.current) {
      audioRef.current.volume = 0.5;
      audioRef.current.play().catch(() => {
        console.log('Autoplay blocked - user interaction required');
      });
    }
    
    return () => {
      // Stop audio when component unmounts
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    };
  }, []);

  const handlePlayAgain = () => {
    // Stop the music before resetting
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    onPlayAgain();
  };

  return (
    <div className="victory-overlay">
      {/* Local audio file for rickroll */}
      <audio 
        ref={audioRef}
        src={rickrollAudio}
        preload="auto"
        loop
      />
      
      <div className="victory-content">
        <h1 className="victory-title">ACCESS GRANTED</h1>
        <p className="victory-subtitle">Welcome to BLVD Dubai</p>
        <p className="victory-rickroll">🎵 Never gonna give you up... 🎵</p>
        <button className="play-again-btn" onClick={handlePlayAgain}>
          Play Again
        </button>
      </div>
    </div>
  );
}
