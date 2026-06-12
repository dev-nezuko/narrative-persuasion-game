import './VictoryScreen.css';
import celebrationAudio from '../assets/audio/never-gonna-give-you-up-rickroll.mp3';
export function VictoryScreen({ onPlayAgain }) {
 return <div className="victory-overlay"><section className="victory-content" aria-label="Game complete"><h1 className="victory-title">ACCESS GRANTED</h1><p className="victory-subtitle">Your fictional night begins.</p><p>This is a game outcome, not a measure of real-world persuasion.</p><audio controls src={celebrationAudio} preload="none" aria-label="Optional celebration music" style={{maxWidth:'100%',margin:'20px auto',display:'block'}}/><button className="play-again-btn" onClick={onPlayAgain}>Play Again</button></section></div>;
}
