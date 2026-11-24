import { getJson } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import type { Metrics } from "../types";

const fetchMetrics = () => getJson<Metrics>("/api/metrics");

export default function MetricsPage() {
  const { data, error } = usePolling(fetchMetrics);
  if (error) return <div className="card empty">Could not load metrics: {error}</div>;
  if (!data) return <div className="card empty">Loading...</div>;

  const items: [string, string | number][] = [
    ["Total incidents", data.total_incidents],
    ["Open incidents", data.open_incidents],
    ["Deduplicated alerts", data.deduplicated_alerts],
    ["Average confidence", `${(data.avg_confidence * 100).toFixed(0)}%`],
    ["Actions succeeded", data.actions_succeeded],
  ];

  return (
    <div className="grid">
      {items.map(([label, value]) => (
        <div key={label} className="card metric">
          <div className="value">{value}</div>
          <div className="label">{label}</div>
        </div>
      ))}
    </div>
  );
}
