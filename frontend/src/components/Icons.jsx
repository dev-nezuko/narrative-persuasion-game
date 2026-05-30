const common = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true, focusable: false };

export function VoiceOnIcon() {
  return <svg {...common}><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M16.5 8.5a5 5 0 0 1 0 7" /><path d="M19 6a8.5 8.5 0 0 1 0 12" /></svg>;
}

export function VoiceOffIcon() {
  return <svg {...common}><path d="M4 9v6h4l5 4V5L8 9H4z" /><path d="M17 9l5 6M22 9l-5 6" /></svg>;
}

export function RestartIcon() {
  return <svg {...common}><path d="M4 12a8 8 0 1 0 2.3-5.6" /><path d="M4 4v4.5h4.5" /></svg>;
}

export function SendIcon({ className }) {
  return <svg {...common} className={className}><path d="M4 12h14" /><path d="M13 6l6 6-6 6" /></svg>;
}
