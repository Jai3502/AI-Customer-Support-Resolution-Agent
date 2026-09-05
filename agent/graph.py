from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.nodes import (
    classify_intent,
    load_memory,
    retrieve_knowledge,
    lookup_customer,
    lookup_order,
    check_escalation,
    generate_response,
    extract_memory,
    save_memory,
)


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("load_memory", load_memory)
    builder.add_node("classify_intent", classify_intent)
    builder.add_node("retrieve_knowledge", retrieve_knowledge)
    builder.add_node("lookup_customer", lookup_customer)
    builder.add_node("lookup_order", lookup_order)
    builder.add_node("check_escalation", check_escalation)
    builder.add_node("generate_response", generate_response)
    builder.add_node("extract_memory", extract_memory)
    builder.add_node("save_memory", save_memory)

    builder.add_edge(START, "load_memory")
    builder.add_edge("load_memory", "classify_intent")
    builder.add_edge("classify_intent", "retrieve_knowledge")
    builder.add_edge("retrieve_knowledge", "lookup_customer")
    builder.add_edge("lookup_customer", "lookup_order")
    builder.add_edge("lookup_order", "check_escalation")
    builder.add_edge("check_escalation", "generate_response")
    builder.add_edge("generate_response", "extract_memory")
    builder.add_edge("extract_memory", "save_memory")
    builder.add_edge("save_memory", END)

    return builder