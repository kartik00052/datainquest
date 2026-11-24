from langgraph.graph import END, START, StateGraph

from daginquest.agent.nodes.classify import classify
from daginquest.agent.nodes.gather_evidence import gather_evidence
from daginquest.agent.nodes.persist_notify import persist_notify
from daginquest.agent.nodes.plan import plan
from daginquest.agent.nodes.policy_gate import policy_gate
from daginquest.agent.nodes.rca import rca
from daginquest.agent.nodes.verify_citations import verify_citations
from daginquest.agent.state import IncidentState


def build_graph():
    g = StateGraph(IncidentState)
    g.add_node("gather_evidence", gather_evidence)
    g.add_node("classify", classify)
    g.add_node("rca", rca)
    g.add_node("verify_citations", verify_citations)
    g.add_node("plan", plan)
    g.add_node("policy_gate", policy_gate)
    g.add_node("persist_notify", persist_notify)

    g.add_edge(START, "gather_evidence")
    g.add_edge("gather_evidence", "classify")
    g.add_edge("classify", "rca")
    g.add_edge("rca", "verify_citations")
    g.add_edge("verify_citations", "plan")
    g.add_edge("plan", "policy_gate")
    g.add_edge("policy_gate", "persist_notify")
    g.add_edge("persist_notify", END)
    # Upgrade path: compile(checkpointer=AsyncPostgresSaver(...)) for resumable runs.
    return g.compile()


graph = build_graph()
