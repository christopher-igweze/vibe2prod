"use client";

interface ScoreGaugeProps {
  score: number;
  label: string;
  size?: number;
}

function scoreColor(score: number): string {
  if (score >= 70) return "#E8913A"; // forge-amber
  if (score >= 40) return "#F4B56A"; // forge-amber-light
  return "#5B8DEF"; // forge-blue
}

export function ScoreGauge({ score, label, size = 160 }: ScoreGaugeProps) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference - (clamped / 100) * circumference;
  const color = scoreColor(clamped);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          className="text-neutral-800"
          strokeWidth={strokeWidth}
        />
        {/* Score arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s ease-out, stroke 0.5s ease" }}
        />
      </svg>
      {/* Center score number — positioned over the SVG */}
      <div
        className="flex items-center justify-center font-bold"
        style={{
          width: size,
          height: size,
          marginTop: -size - 8, // overlap SVG
          color,
          fontSize: size * 0.28,
          transition: "color 0.5s ease",
        }}
      >
        {clamped}
      </div>
      <p className="text-sm text-neutral-400">{label}</p>
    </div>
  );
}
