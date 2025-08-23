import React from "react";

type Props = {
  /** 0..1 */
  value: number;
  size?: number;        // px
  strokeWidth?: number; // px
  thresholds?: { green: number; amber: number }; // fraction boundaries
  title?: string;       // label displayed below donut
  loading?: boolean;    // show skeleton while loading
  className?: string;   // additional styling
};

export default function DonutGauge({
  value,
  size = 80,
  strokeWidth = 4,
  thresholds = { green: 0.9, amber: 0.6 },
  title,
  loading = false,
  className = "",
}: Props) {
  // Prevent flicker by using last known value while loading
  const [lastValue, setLastValue] = React.useState(value);
  React.useEffect(() => {
    if (!loading && value !== undefined) {
      setLastValue(value);
    }
  }, [value, loading]);

  const displayValue = loading ? lastValue : value;
  const clamped = Math.max(0, Math.min(1, displayValue ?? 0));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = circumference * (1 - clamped);

  let color = "#ef4444"; // red
  if (clamped >= thresholds.green) color = "#22c55e"; // green
  else if (clamped >= thresholds.amber) color = "#f59e0b"; // amber

  const percentage = Math.round(clamped * 100);

  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <div className="relative">
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="shrink-0"
          role="img"
          aria-label={title ? `${title}: ${percentage}%` : `gauge: ${percentage}%`}
          aria-valuenow={percentage}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          {/* Background circle */}
          <circle
            cx={size/2} cy={size/2} r={radius}
            stroke="#374151" strokeWidth={strokeWidth}
            fill="none"
            opacity={0.3}
          />
          {/* Progress circle */}
          <circle
            cx={size/2} cy={size/2} r={radius}
            stroke={color} strokeWidth={strokeWidth}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={progress}
            strokeLinecap="round"
            transform={`rotate(-90 ${size/2} ${size/2})`}
            className="transition-all duration-300 ease-out"
          />
          {/* Percentage text inside */}
          <text
            x="50%" y="50%" dominantBaseline="middle" textAnchor="middle"
            fontSize={size * 0.25} fontWeight={600} fill="#ffffff"
            fontFamily="Inter, system-ui, sans-serif"
            className="transition-opacity duration-200"
            opacity={loading ? 0.5 : 1}
          >
            {loading ? "..." : `${percentage}%`}
          </text>
        </svg>
        {/* Loading skeleton overlay */}
        {loading && (
          <div className="absolute inset-0 bg-neutral-800/20 rounded-full animate-pulse" />
        )}
      </div>
      {/* Label below donut */}
      {title && (
        <div className="text-sm font-medium text-zinc-400 text-center leading-tight">
          {title}
        </div>
      )}
    </div>
  );
}
