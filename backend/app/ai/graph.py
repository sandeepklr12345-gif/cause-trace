"""The LangGraph workflow.

route ─┬─ ingest ───┐
       ├─ edit ─────┼─▶ hypothesize ─▶ critic ─▶ plan (gaps + CAPA) ─▶ finalize
       │   (edit skips straight to finalize when only an identifier such as the batch number changed)
       ├─ analyze ──┘
       ├─ challenge ─▶ critic ─▶ (finalize)         [shortcut: only re-check the reasoning]
       └─ question ──▶ answer ─▶ finalize
"""
from langgraph.graph import END, START, StateGraph

from . import nodes
from .nodes import State


def after_critic(state: State) -> str:
    return "finalize" if state["intent"] == "challenge" else "plan"


def build_graph():
    g = StateGraph(State)
    for name in ("route", "ingest", "edit", "hypothesize", "critic", "plan", "answer", "finalize"):
        g.add_node(name, getattr(nodes, name))
    g.add_edge(START, "route")
    g.add_conditional_edges("route", nodes.pick_branch,
                            {"ingest": "ingest", "edit": "edit", "hypothesize": "hypothesize",
                             "critic": "critic", "answer": "answer"})
    g.add_edge("ingest", "hypothesize")
    g.add_conditional_edges("edit", nodes.after_edit, {"hypothesize": "hypothesize", "finalize": "finalize"})
    g.add_edge("hypothesize", "critic")
    g.add_conditional_edges("critic", after_critic, {"plan": "plan", "finalize": "finalize"})
    g.add_edge("plan", "finalize")
    g.add_edge("answer", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


graph = build_graph()
