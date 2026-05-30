import './InfluenceMeter.css';

export function InfluenceMeter({ score, threshold, accessGranted }) {
  const percentage = Math.max(0, Math.min(100, (score / threshold) * 100));
  const isNegative = score < 0;

  const getMeterClass = () => {
    if (accessGranted) return 'winning';
    if (isNegative) return 'negative';
    return 'positive';
  };

  return (
    <div className="influence-meter">
      <p className="meter-title" id="meter-label">
        <span>Influence</span>
        <span className="meter-goal">{threshold} to get in</span>
      </p>
      <div className="meter-track" role="progressbar" aria-labelledby="meter-label" aria-valuemin={-50} aria-valuemax={threshold} aria-valuenow={score}>
        <div 
          className={`meter-fill ${getMeterClass()}`}
          style={{ width: `${percentage}%` }}
        />
        <div className="meter-text">
          {accessGranted ? 'Access granted' : `${Math.round(percentage)}%`}
        </div>
      </div>
    </div>
  );
}
