from agent.graph import build_graph


def create_agent(checkpointer, store):
    """
    Compile the LangGraph agent.

    checkpointer -> gives short-term / thread-scoped memory (SqliteSaver)
    store        -> gives long-term / cross-thread memory (SqliteStore),
                     required because load_memory/save_memory nodes are
                     injected with `store` via their keyword-only argument.
    """
    builder = build_graph()
    graph = builder.compile(checkpointer=checkpointer, store=store)
    return graph