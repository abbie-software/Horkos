export default function ScoreRing({
  score,
  strokeClass,
}: {
  score: number;
  strokeClass: string;
}) {
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(Math.max(score, 0), 100) / 100;

  return (
    <div
      className="relative h-24 w-24 shrink-0"
      role="img"
      aria-label={`Trust score ${score} out of 100`}
    >
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90" aria-hidden="true">
        <circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          strokeWidth="7"
          className="stroke-border"
        />
        {pct > 0 && (
          <circle
            cx="40"
            cy="40"
            r={radius}
            fill="none"
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={`${circumference * pct} ${circumference}`}
            className={strokeClass}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center leading-tight">
        <span className="font-serif text-xl font-semibold">{score}</span>
        <span className="text-[10px] text-muted">/ 100</span>
      </div>
    </div>
  );
}