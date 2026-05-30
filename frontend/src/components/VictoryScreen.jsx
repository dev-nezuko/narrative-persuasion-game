import './VictoryScreen.css';

export function VictoryScreen({ onPlayAgain }) {
  return (
    <div className="victory-overlay">
      <section className="victory-content" role="dialog" aria-modal="false" aria-labelledby="victory-title">
        <h2 id="victory-title" className="victory-title">Access Granted</h2>
        <p className="victory-subtitle">The rope comes down. Your fictional night begins.</p>
        <p className="victory-note">A game outcome, not a measure of real-world persuasion.</p>
        {/* Focus the only action so keyboard players are not left behind the overlay */}
        <button type="button" className="play-again-btn" onClick={onPlayAgain} autoFocus>Play again</button>
      </section>
    </div>
  );
}
