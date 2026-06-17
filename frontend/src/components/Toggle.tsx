import React from 'react';

interface ToggleProps {
  checked: boolean;
  onChange: (val: boolean) => void;
  disabled?: boolean;
}

export const Toggle: React.FC<ToggleProps> = ({ checked, onChange, disabled = false }) => {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      className={`relative inline-flex h-[22px] w-[40px] shrink-0 cursor-pointer rounded-full border transition-all duration-300 ease-in-out focus:outline-none ${
        checked
          ? 'bg-accent/20 border-accent/40 shadow-[0_0_8px_rgba(79,70,229,0.15)]'
          : 'bg-slate-100 border-slate-200/80'
      } ${disabled ? 'opacity-30 cursor-not-allowed' : ''}`}
    >
      <span
        className={`pointer-events-none inline-block h-[16px] w-[16px] transform rounded-full transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] mt-[2px] ${
          checked
            ? 'translate-x-[18px] bg-accent shadow-[0_0_6px_rgba(79,70,229,0.3)]'
            : 'translate-x-[2px] bg-slate-400'
        }`}
      />
    </button>
  );
};
