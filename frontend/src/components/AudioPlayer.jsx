import { useEffect, useRef } from 'react';

export function AudioPlayer({ audioBase64, onFinished }) {
  const audioRef = useRef(null);

  useEffect(() => {
    if (audioBase64 && audioRef.current) {
      // Create audio URL from base64
      const audioBlob = base64ToBlob(audioBase64, 'audio/mpeg');
      const audioUrl = URL.createObjectURL(audioBlob);
      
      audioRef.current.src = audioUrl;
      audioRef.current.play().catch(err => {
        console.log('Audio autoplay blocked:', err);
      });

      // Cleanup URL when done
      return () => {
        URL.revokeObjectURL(audioUrl);
      };
    }
  }, [audioBase64]);

  const handleEnded = () => {
    if (onFinished) {
      onFinished();
    }
  };

  return (
    <audio 
      ref={audioRef} 
      onEnded={handleEnded}
      style={{ display: 'none' }}
    />
  );
}

// Helper to convert base64 to Blob
function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}

