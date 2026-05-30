import { useEffect, useRef } from 'react';

export function AudioPlayer({ audioBase64, onFinished }) {
  const audioRef = useRef(null);

  useEffect(() => {
    if (audioBase64 && audioRef.current) {
      const audioBlob = base64ToBlob(audioBase64, 'audio/mpeg');
      const audioUrl = URL.createObjectURL(audioBlob);
      
      audioRef.current.src = audioUrl;
      // Browsers may block playback without a prior gesture; the text reply still shows.
      audioRef.current.play().catch(() => {});

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

function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}

