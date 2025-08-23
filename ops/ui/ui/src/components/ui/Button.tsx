import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
  loading?: boolean;
  children: React.ReactNode;
}

export function PrimaryButton({ 
  children, 
  loading = false, 
  disabled, 
  className = "", 
  ...props 
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-2 px-4 py-2 
        bg-emerald-600 hover:bg-emerald-700 focus:bg-emerald-700
        text-white font-medium text-sm rounded-lg
        transition-all duration-200 ease-out
        focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:ring-offset-2 focus:ring-offset-neutral-900
        hover:shadow-[0_0_0_2px_rgba(16,185,129,.25)] hover:shadow-lg
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none
        ${className}
      `}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}

export function SecondaryButton({ 
  children, 
  loading = false, 
  disabled, 
  className = "", 
  ...props 
}: ButtonProps) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`
        inline-flex items-center justify-center gap-2 px-4 py-2 
        bg-neutral-700 hover:bg-neutral-600 focus:bg-neutral-600
        text-neutral-200 font-medium text-sm rounded-full
        transition-all duration-200 ease-out
        focus:outline-none focus:ring-2 focus:ring-neutral-500/50 focus:ring-offset-2 focus:ring-offset-neutral-900
        hover:shadow-md
        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none
        ${className}
      `}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
