import uuid
import streamlit as st

from memory.runtime import Persistence
from memory.manager import MemoryManager
from agent.runtime import create_agent
from tools.customer_lookup import list_all_customers, get_customer

st.set_page_config(
    page_title="AI Customer Support Agent",
    page_icon="🎧",
    layout="wide",
)


# ---------------------------------------------------------------------------
# One-time persistence + compiled graph, cached across reruns
# ---------------------------------------------------------------------------
@st.cache_resource
def get_persistence():
    return Persistence()


persistence = get_persistence()
graph = create_agent(
    checkpointer=persistence.checkpointer,
    store=persistence.store,
)
memory_mgr = MemoryManager(persistence.store)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "customer_id" not in st.session_state:
    st.session_state.customer_id = "CUST001"

# ---------------------------------------------------------------------------
# Sidebar: Customer Selector & Context Explorer
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("👤 Customer Profile")

    all_customers = list_all_customers()
    options = {
        f"{c.get('name', cid)} ({cid})": cid for cid, c in all_customers.items()
    }
    options["Custom Customer ID"] = "CUSTOM"

    default_index = 0
    option_keys = list(options.keys())
    for idx, key in enumerate(option_keys):
        if options[key] == st.session_state.customer_id:
            default_index = idx

    selected_option = st.selectbox(
        "Select Active Customer",
        options=option_keys,
        index=default_index,
    )

    if options[selected_option] == "CUSTOM":
        st.session_state.customer_id = st.text_input(
            "Enter Custom Customer ID",
            value=st.session_state.customer_id,
        )
    else:
        st.session_state.customer_id = options[selected_option]

    # Show active customer details card
    active_customer = get_customer(st.session_state.customer_id)
    if isinstance(active_customer, dict) and "name" in active_customer:
        st.subheader(f"✨ {active_customer.get('name')}")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Tier:** `{active_customer.get('membership')}`")
            st.markdown(f"**Language:** `{active_customer.get('preferred_language')}`")
        with col2:
            st.markdown(f"**Orders:** `{active_customer.get('total_orders')}`")
            st.markdown(f"**City:** `{active_customer.get('city')}`")

        if active_customer.get("notes"):
            st.caption(f"ℹ️ {active_customer.get('notes')}")
    else:
        st.info(f"Customer ID: `{st.session_state.customer_id}`")

    st.divider()
    st.header("🧠 Long-Term Memory")

    stored_memories = memory_mgr.get_all_user_memories(st.session_state.customer_id)
    if stored_memories:
        for m in stored_memories:
            st.markdown(f"• {m}")
    else:
        st.caption("No long-term memories saved yet.")

    st.divider()
    st.caption(f"Session Thread ID: `{st.session_state.thread_id[:8]}...`")

    if st.button("🆕 New Conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

# ---------------------------------------------------------------------------
# Main Chat Area
# ---------------------------------------------------------------------------
st.title("🎧 AI Customer Support & Resolution Agent")
st.caption("Powered by LangGraph, Gemini 3.5, Structured Data & Short/Long-Term Memory")

# Render existing chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
user_input = st.chat_input("How can I help you today?")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.status("Processing request...", expanded=False) as status:
            try:
                config = {
                    "configurable": {
                        "thread_id": st.session_state.thread_id,
                    }
                }

                result = graph.invoke(
                    {
                        "user_id": st.session_state.customer_id,
                        "user_message": user_input,
                    },
                    config=config,
                )

                response = result.get(
                    "response", "I was unable to generate a response."
                )

                steps = result.get("agent_steps", [])
                status.update(
                    label=f"✅ Completed ({len(steps)} steps)",
                    state="complete",
                )

                st.markdown(response)

                # Append assistant response to session state
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )

                if result.get("requires_human"):
                    ticket = result.get("ticket_data", {})
                    if ticket:
                        st.info(
                            f"🎫 **Escalated to Support**: Ticket `{ticket.get('ticket_id', 'N/A')}` "
                            f"created with `{ticket.get('priority', 'Medium')}` priority."
                        )

            except Exception as e:
                status.update(label="❌ Agent Error", state="error")
                st.error(str(e))

        # Force UI refresh to update memory viewer sidebar if memory was saved
        st.rerun()