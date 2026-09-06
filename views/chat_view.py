import uuid
import streamlit as st
from memory.manager import MemoryManager
from tools.customer_lookup import list_all_customers, get_customer
from tools.ticket import get_customer_tickets, create_ticket


def render_chat_view(graph, memory_mgr: MemoryManager):
    """Render 🎧 AI Customer Support & Resolution Chat view."""

    is_admin = st.session_state.get("role") == "admin"
    user_name = st.session_state.get("user", {}).get("name", "User")

    st.title("🎧 AI Customer Support & Resolution Agent")
    st.caption("Powered by LangGraph, Gemini 3.5, Short/Long-Term Memory & Ticket Escalation")

    # --- Active Customer Selector / Card ---
    with st.sidebar:
        st.header("👤 Customer Profile Context")

        all_customers = list_all_customers()

        if is_admin:
            # Admin can switch active customer profile for testing/support
            st.caption("⚡ **Admin Mode**: Select active customer context")
            options = {f"{c.get('name', cid)} ({cid})": cid for cid, c in all_customers.items()}
            options["Custom Customer ID"] = "CUSTOM"

            default_idx = 0
            opt_keys = list(options.keys())
            for idx, k in enumerate(opt_keys):
                if options[k] == st.session_state.customer_id:
                    default_idx = idx

            selected_opt = st.selectbox("Active Customer Profile", opt_keys, index=default_idx)

            if options[selected_opt] == "CUSTOM":
                st.session_state.customer_id = st.text_input("Enter Custom Customer ID", value=st.session_state.customer_id)
            else:
                st.session_state.customer_id = options[selected_opt]
        else:
            # Customer role is bound to their own customer ID
            c_info = get_customer(st.session_state.customer_id)
            st.markdown(f"**Logged in as:** `{user_name}` (`{st.session_state.customer_id}`)")

        active_customer = get_customer(st.session_state.customer_id)
        if isinstance(active_customer, dict) and "name" in active_customer:
            st.subheader(f"✨ {active_customer.get('name')}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Tier:** `{active_customer.get('membership')}`")
                st.markdown(f"**Lang:** `{active_customer.get('preferred_language')}`")
            with col2:
                st.markdown(f"**Orders:** `{active_customer.get('total_orders')}`")
                st.markdown(f"**City:** `{active_customer.get('city')}`")

            if active_customer.get("notes"):
                st.caption(f"ℹ️ {active_customer.get('notes')}")

        st.divider()

        # --- User's Active Tickets ---
        st.header("🎫 My Support Tickets")
        my_tickets = get_customer_tickets(st.session_state.customer_id)
        if my_tickets:
            for t in my_tickets:
                st.caption(f"• `{t.get('ticket_id')}` [{t.get('status')}] - {t.get('category')}")
        else:
            st.caption("No open tickets.")

        st.divider()

        # --- Long-Term Memory Section ---
        st.header("🧠 Agent Long-Term Memory")
        mems = memory_mgr.get_all_user_memories(st.session_state.customer_id)
        if mems:
            for m in mems:
                st.markdown(f"• {m}")
        else:
            st.caption("No long-term memories saved yet.")

        st.divider()
        st.caption(f"Session Thread: `{st.session_state.thread_id[:8]}...`")

        if st.button("🆕 New Conversation", use_container_width=True):
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()

    # --- Main Chat Messaging Interface ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_input = st.chat_input("Ask a question about your order, returns, or support...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.status("Thinking & Resolving...", expanded=False) as status:
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

                    response = result.get("response", "I was unable to generate a response.")
                    steps = result.get("agent_steps", [])
                    status.update(
                        label=f"✅ Done ({len(steps)} steps)",
                        state="complete",
                    )

                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                    if result.get("requires_human"):
                        ticket = result.get("ticket_data", {})
                        if ticket:
                            st.info(
                                f"🎫 **Ticket Created**: `{ticket.get('ticket_id', 'N/A')}` "
                                f"[{ticket.get('priority', 'Medium')}] - Escalated to human support team."
                            )

                except Exception as e:
                    status.update(label="❌ Error processing request", state="error")
                    st.error(str(e))

            st.rerun()
