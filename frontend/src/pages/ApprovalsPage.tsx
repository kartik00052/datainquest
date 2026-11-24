import { getJson, post } from "../api/client";
import ConfidenceBadge from "../components/ConfidenceBadge";
import { usePolling } from "../hooks/usePolling";
import type { PendingAction } from "../types";

const fetchPending = () => getJson<PendingAction[]>("/api/actions/pending");

export default function ApprovalsPage() {
  const { data, error, refresh } = usePolling(fetchPending, 5000);

  const decide = async (id: number, verb: "approve" | "reject") => {
    try {
      await post(`/api/actions/${id}/${verb}`);
    } finally {
      refresh();
    }
  };

  if (error) return <div className="card empty">Could not load approvals: {error}</div>;
  if (!data || data.length === 0) return <div className="card empty">Nothing waiting for approval.</div>;

  return (
    <div className="card table-wrap">
      <table>
        <thead>
          <tr><th>Action</th><th>Target</th><th>Confidence</th><th>Cause</th><th /></tr>
        </thead>
        <tbody>
          {data.map((a) => (
            <tr key={a.id}>
              <td>#{a.id} {a.type}</td>
              <td>{a.dag_id}.{a.task_id}</td>
              <td><ConfidenceBadge value={a.confidence} /></td>
              <td>{a.root_cause ?? "-"}</td>
              <td>
                <button className="btn primary" onClick={() => decide(a.id, "approve")}>Approve</button>
                <button className="btn" onClick={() => decide(a.id, "reject")}>Reject</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
