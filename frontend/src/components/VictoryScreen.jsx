import './VictoryScreen.css';
export function VictoryScreen({ onPlayAgain }) {
 return <div className="victory-overlay"><section className="victory-content" aria-label="Game complete"><h1 className="victory-title">ACCESS GRANTED</h1><p className="victory-subtitle">Your fictional night begins.</p><p>This is a game outcome, not a measure of real-world persuasion.</p><button className="play-again-btn" onClick={onPlayAgain}>Play Again</button></section></div>;
}
