import React from "react";

type Props = {
  /** 0..1 */
  value: number;
  size?: number;        // px
  strokeWidth?: number; // px
  thresholds?: { green: number; amber: number }; // fraction boundaries
};

export default function DonutGauge({
  value,
  size = 28,
  strokeWidth = 4,
  thresholds = { green: 0.9, amber: 0.6 },
}: Props) {
  const clamped = Math.max(0, Math.min(1, value ?? 0));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = circumference * (1 - clamped);

  let color = "#ef4444"; // red
  if (clamped >= thresholds.green) color = "#22c55e"; // green
  else if (clamped >= thresholds.amber) color = "#f59e0b"; // amber

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      <circle
        cx={size/2} cy={size/2} r={radius}
        stroke="#e5e7eb" strokeWidth={strokeWidth}
        fill="none"
      />
      <circle
        cx={size/2} cy={size/2} r={radius}
        stroke={color} strokeWidth={strokeWidth}
        fill="none"
        strokeDasharray={circumference}
        strokeDashoffset={progress}
        strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}
      />
      <text
        x="50%" y="50%" dominantBaseline="middle" textAnchor="middle"
        fontSize={size * 0.32} fontWeight={600} fill="#111827"
      >
        {Math.round(clamped * 100)}
      </text>
    </svg>
  );
}
