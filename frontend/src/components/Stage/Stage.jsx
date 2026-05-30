import { Skyline } from './Skyline';
import { Door } from './Door';
import { CharacterColumn } from './CharacterColumn';
import './Stage.css';

export function Stage({ 
  playerMessage, 
  doormanMessage, 
  isLoading, 
  isOpen 
}) {
  return (
    <div className="stage">
      {/* Background */}
      <Skyline />
      
      {/* Three Column Layout */}
      <div className="stage-content">
        {/* Left: Player */}
        <CharacterColumn 
          type="player" 
          message={playerMessage}
        />
        
        {/* Center: Door */}
        <Door isOpen={isOpen} />
        
        {/* Right: Doorman */}
        <CharacterColumn 
          type="doorman" 
          message={doormanMessage}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

