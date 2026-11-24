import { getJson } from "../api/client";
import ConfidenceBadge from "../components/ConfidenceBadge";
import { usePolling } from "../hooks/usePolling";
import type { Incident } from "../types";

const fetchIncidents = () => getJson<Incident[]>("/api/incidents");

export default function IncidentsPage() {
  const { data, error } = usePolling(fetchIncidents);

  if (error) return <div className="card empty">Could not load incidents: {error}</div>;
  if (!data || data.length === 0) return <div className="card empty">No incidents yet.</div>;

  return (
    <div className="card table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th><th>DAG / task</th><th>Category</th><th>Confidence</th>
            <th>Status</th><th>Seen</th><th>Cause</th>
          </tr>
        </thead>
        <tbody>
          {data.map((i) => (
            <tr key={i.id}>
              <td>{i.id}</td>
              <td>{i.dag_id}.{i.task_id}</td>
              <td>{i.category ?? "-"}</td>
              <td><ConfidenceBadge value={i.confidence} /></td>
              <td><span className="pill">{i.status}</span></td>
              <td>{i.occurrences}x</td>
              <td>{i.root_cause ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
