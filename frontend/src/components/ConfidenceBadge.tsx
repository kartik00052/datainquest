export default function ConfidenceBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="pill">n/a</span>;
  const color = value >= 0.75 ? "var(--good)" : value >= 0.5 ? "var(--warn)" : "var(--bad)";
  return (
    <span className="pill" style={{ color, borderColor: color }}>
      {(value * 100).toFixed(0)}%
    </span>
  );
}
