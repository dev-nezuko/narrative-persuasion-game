import './Skyline.css';

export function Skyline() {
  return (
    <div className="skyline">
      <div className="buildings">
        <div className="building" style={{ width: '32px', height: '128px' }} />
        <div className="building" style={{ width: '48px', height: '192px' }} />
        <div className="building" style={{ width: '24px', height: '96px' }} />
        <div className="building" style={{ width: '64px', height: '256px', opacity: 0.6 }} />
        <div className="building" style={{ width: '40px', height: '160px' }} />
        <div className="building" style={{ width: '32px', height: '224px', opacity: 0.4 }} />
        <div className="building" style={{ width: '56px', height: '144px' }} />
      </div>
    </div>
  );
}

