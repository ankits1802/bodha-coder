interface CheckMarkProps {
  className?: string;
}

export function CheckMark({ className = "" }: CheckMarkProps) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" className={className}>
      <path d="M2.5 6.4l2.3 2.3 4.7-5.2" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
