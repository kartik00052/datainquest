import { useState } from "react";
import ApprovalsPage from "./pages/ApprovalsPage";
import IncidentsPage from "./pages/IncidentsPage";
import MetricsPage from "./pages/MetricsPage";

type Tab = "incidents" | "approvals" | "metrics";
const TABS: Tab[] = ["incidents", "approvals", "metrics"];

export default function App() {
  const [tab, setTab] = useState<Tab>("incidents");

  return (
    <div className="app">
      <h1>DagInquest</h1>
      <div className="nav">
        {TABS.map((t) => (
          <button key={t} className={t === tab ? "active" : ""} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>
      {tab === "incidents" && <IncidentsPage />}
      {tab === "approvals" && <ApprovalsPage />}
      {tab === "metrics" && <MetricsPage />}
    </div>
  );
}
