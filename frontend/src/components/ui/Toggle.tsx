interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Toggle({ label, checked, onChange, disabled = false }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative h-6.5 w-10.5 flex-none cursor-pointer rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${checked ? "bg-ok" : "bg-separator"}`}
    >
      <span
        aria-hidden="true"
        className={`absolute top-0.5 size-5.5 rounded-full bg-white shadow-knob transition-[left] ${checked ? "left-4.5" : "left-0.5"}`}
      />
    </button>
  );
}
