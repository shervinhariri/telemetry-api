import React from "react";

type Props = {
  value: number;          // 0..100
  size?: number;          // px
  stroke?: number;        // px
  className?: string;
  label?: string;         // shown outside, below the ring
};

export default function SuccessRing({
  value,
  size = 120,
  stroke = 10,
  className = "",
  label = "Success Rate",
}: Props) {
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value ?? 0));
  const dash = (clamped / 100) * circumference;
  // No glow for a cleaner, more professional appearance
  const glow = '';

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <svg width={size} height={size} className="block">
        <defs>
          <linearGradient id="sr-grad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6EFACC" />
            <stop offset="100%" stopColor="#2DE3C4" />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="url(#sr-grad)"
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={`${dash} ${circumference - dash}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className={glow}
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="middle"
          textAnchor="middle"
          className="fill-white"
          style={{ fontSize: size * 0.26, fontWeight: 700, letterSpacing: "-0.02em" }}
        >
          {clamped.toFixed(1)}%
        </text>
      </svg>
      <div className="mt-3 text-sm text-zinc-400">{label}</div>
    </div>
  );
}
