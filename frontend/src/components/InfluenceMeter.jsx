import './InfluenceMeter.css';

export function InfluenceMeter({ score, threshold, accessGranted }) {
  const percentage = Math.max(0, Math.min(100, (score / threshold) * 100));
  const displayScore = Math.max(0, score);
  const isNegative = score < 0;

  const getMeterClass = () => {
    if (accessGranted) return 'winning';
    if (isNegative) return 'negative';
    return 'positive';
  };

  return (
    <div className="influence-meter">
      <h2 className="meter-title">INFLUENCE METER</h2>
      <div className="meter-track">
        <div 
          className={`meter-fill ${getMeterClass()}`}
          style={{ width: `${percentage}%` }}
        />
        <div className="meter-text">
          {accessGranted ? 'ACCESS GRANTED' : `${Math.round(percentage)}%`}
        </div>
      </div>
    </div>
  );
}
