import streamlit as st
from datetime import datetime
from auth import (
    has_permission,
    load_users,
    update_user_role,
    PERM_DELETE_TICKETS,
    PERM_MANAGE_ROLES,
    PERM_MANAGE_TICKETS,
    PERM_EDIT_CUSTOMERS,
    PERM_UPDATE_ORDERS,
)
from tools.ticket import (
    get_all_tickets,
    update_ticket_status,
    update_ticket_priority,
    delete_ticket,
)
from tools.customer_lookup import (
    list_all_customers,
    get_customer,
    update_customer_notes,
    update_customer_membership,
)
from tools.order_lookup import (
    list_all_orders,
    update_order_status,
)
from memory.manager import MemoryManager
from database.pg_client import check_connection_status, is_postgres_available
from database.schema import init_db_and_seed, get_table_counts
from database.vector_db import reindex_knowledge_base, search_knowledge_vectors


def render_admin_dashboard(memory_mgr: MemoryManager):

    """Render 👨💼 Customer Support Admin Operations Desk with RBAC protection."""
    user_role = st.session_state.get("role", "customer")

    st.title("👨💼 Customer Support Operations & RBAC Control Desk")
    st.caption("Manage support tickets, customer profiles, long-term memories, order fulfillment, user role access, and PostgreSQL/Vector DB infrastructure.")

    # --- Top KPI Summary Cards ---
    tickets = get_all_tickets()
    customers = list_all_customers()
    orders = list_all_orders()

    open_count = sum(1 for t in tickets if t.get("status") == "Open")
    in_prog_count = sum(1 for t in tickets if t.get("status") == "In Progress")
    high_prio_count = sum(1 for t in tickets if t.get("priority") == "High" and t.get("status") in ["Open", "In Progress"])
    total_cust = len(customers)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🚨 Open Tickets", open_count, delta=f"{open_count} pending", delta_color="inverse")
    m2.metric("⏳ In Progress", in_prog_count)
    m3.metric("🔥 High Priority", high_prio_count, delta="Immediate Action Needed" if high_prio_count > 0 else "Normal", delta_color="off")
    m4.metric("👥 Total Customers", total_cust)

    st.divider()

    # --- Sub-navigation Tabs ---
    tabs_list = [
        "🎫 Ticket Operations Desk",
        "👥 Customer Profiles & Memory",
        "📦 Order Oversight & Fulfillment",
        "🐘 PostgreSQL & 🎯 Vector DB",
    ]

    if has_permission(user_role, PERM_MANAGE_ROLES):
        tabs_list.append("🔑 User Role Access Control")

    admin_tabs = st.tabs(tabs_list)

    # ---------------------------------------------------------------------------
    # Tab 1: Ticket Operations Desk
    # ---------------------------------------------------------------------------
    with admin_tabs[0]:
        st.subheader("🎫 Active & Escalated Support Tickets")

        # Filters
        fcol1, fcol2, fcol3 = st.columns([2, 2, 3])
        with fcol1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All Statuses", "Open", "In Progress", "Resolved", "Closed"],
                key="admin_status_filter",
            )
        with fcol2:
            prio_filter = st.selectbox(
                "Filter by Priority",
                ["All Priorities", "High", "Medium", "Low"],
                key="admin_prio_filter",
            )
        with fcol3:
            search_query = st.text_input(
                "🔍 Search Tickets",
                placeholder="Search ticket ID, customer ID, or keyword...",
                key="admin_ticket_search",
            )

        # Apply filters
        filtered_tickets = tickets
        if status_filter != "All Statuses":
            filtered_tickets = [t for t in filtered_tickets if t.get("status") == status_filter]
        if prio_filter != "All Priorities":
            filtered_tickets = [t for t in filtered_tickets if t.get("priority") == prio_filter]
        if search_query:
            sq = search_query.lower()
            filtered_tickets = [
                t for t in filtered_tickets
                if sq in t.get("ticket_id", "").lower()
                or sq in t.get("customer_id", "").lower()
                or sq in t.get("description", "").lower()
                or sq in t.get("category", "").lower()
            ]

        st.caption(f"Showing {len(filtered_tickets)} of {len(tickets)} total tickets")

        if not filtered_tickets:
            st.info("No support tickets match the selected criteria.")
        else:
            for ticket in filtered_tickets:
                t_id = ticket.get("ticket_id")
                t_cust_id = ticket.get("customer_id")
                t_status = ticket.get("status", "Open")
                t_prio = ticket.get("priority", "Medium")
                t_cat = ticket.get("category", "General")
                t_desc = ticket.get("description", "")
                t_agent = ticket.get("assigned_agent", "Unassigned")
                t_notes = ticket.get("resolution_notes", "")
                t_created = ticket.get("created_at", "")[:19].replace("T", " ")

                prio_badge = "🔴 High" if t_prio == "High" else ("🟡 Medium" if t_prio == "Medium" else "🟢 Low")
                status_badge = "🟢 Resolved" if t_status in ["Resolved", "Closed"] else ("🟡 In Progress" if t_status == "In Progress" else "🔴 Open")

                customer_info = get_customer(t_cust_id)
                cust_name = customer_info.get("name", t_cust_id) if isinstance(customer_info, dict) else t_cust_id

                expander_title = f"{status_badge} | `{t_id}` - {cust_name} ({t_cust_id}) | {prio_badge} | {t_cat}"

                with st.expander(expander_title, expanded=(t_status == "Open" and t_prio == "High")):
                    tcol1, tcol2 = st.columns([3, 2])

                    with tcol1:
                        st.markdown(f"**Ticket ID:** `{t_id}`")
                        st.markdown(f"**Customer:** `{cust_name}` (`{t_cust_id}`)")
                        st.markdown(f"**Category:** `{t_cat}`")
                        st.markdown(f"**Created:** `{t_created}`")
                        st.markdown(f"**Description:**\n>{t_desc}")

                    with tcol2:
                        st.markdown("### ✏️ Update Ticket Status")

                        can_manage = has_permission(user_role, PERM_MANAGE_TICKETS)
                        can_delete = has_permission(user_role, PERM_DELETE_TICKETS)

                        new_status = st.selectbox(
                            "Status",
                            ["Open", "In Progress", "Resolved", "Closed"],
                            index=["Open", "In Progress", "Resolved", "Closed"].index(t_status) if t_status in ["Open", "In Progress", "Resolved", "Closed"] else 0,
                            key=f"status_sel_{t_id}",
                            disabled=not can_manage,
                        )

                        new_prio = st.selectbox(
                            "Priority Level",
                            ["High", "Medium", "Low"],
                            index=["High", "Medium", "Low"].index(t_prio) if t_prio in ["High", "Medium", "Low"] else 1,
                            key=f"prio_sel_{t_id}",
                            disabled=not can_manage,
                        )

                        agent_name = st.text_input(
                            "Assigned Agent",
                            value=t_agent if t_agent != "Unassigned" else "Admin Agent",
                            key=f"agent_in_{t_id}",
                            disabled=not can_manage,
                        )

                        res_notes = st.text_area(
                            "Resolution / Support Notes",
                            value=t_notes,
                            placeholder="Add action taken or response notes...",
                            key=f"notes_in_{t_id}",
                            disabled=not can_manage,
                        )

                        scol1, scol2 = st.columns(2)
                        with scol1:
                            if st.button("💾 Save Ticket", key=f"save_btn_{t_id}", use_container_width=True, disabled=not can_manage):
                                update_ticket_status(
                                    ticket_id=t_id,
                                    status=new_status,
                                    resolution_notes=res_notes,
                                    agent_name=agent_name,
                                )
                                update_ticket_priority(t_id, new_prio)
                                st.success(f"Ticket {t_id} updated successfully!")
                                st.rerun()

                        with scol2:
                            if can_delete:
                                if st.button("🗑️ Delete", key=f"del_btn_{t_id}", use_container_width=True):
                                    delete_ticket(t_id)
                                    st.warning(f"Ticket {t_id} removed.")
                                    st.rerun()
                            else:
                                st.caption("🔒 *Deletion requires Admin role*")

    # ---------------------------------------------------------------------------
    # Tab 2: Customer Profiles & Memory Manager
    # ---------------------------------------------------------------------------
    with admin_tabs[1]:
        st.subheader("👥 Customer Directory & Memory Inspector")

        c_options = {f"{c.get('name', cid)} ({cid})": cid for cid, c in customers.items()}
        if c_options:
            selected_c_key = st.selectbox("Select Customer to Inspect / Edit", list(c_options.keys()))
            selected_cid = c_options[selected_c_key]
            cust_data = customers.get(selected_cid, {})

            cp_col1, cp_col2 = st.columns([1, 1])

            with cp_col1:
                st.markdown("### 📋 Profile Card")
                st.markdown(f"**Customer ID:** `{cust_data.get('customer_id')}`")
                st.markdown(f"**Full Name:** `{cust_data.get('name')}`")
                st.markdown(f"**Email:** `{cust_data.get('email')}`")
                st.markdown(f"**Phone:** `{cust_data.get('phone')}`")
                st.markdown(f"**City / State:** `{cust_data.get('city')}, {cust_data.get('state')}`")
                st.markdown(f"**Total Orders:** `{cust_data.get('total_orders')}`")

                st.divider()

                can_edit_cust = has_permission(user_role, PERM_EDIT_CUSTOMERS)

                st.markdown("### 🏷️ Edit Membership Tier")
                current_mem = cust_data.get("membership", "Standard")
                new_mem = st.selectbox(
                    "Membership Tier",
                    ["Standard", "Gold", "VIP Platinum"],
                    index=["Standard", "Gold", "VIP Platinum"].index(current_mem) if current_mem in ["Standard", "Gold", "VIP Platinum"] else 0,
                    key="admin_mem_edit",
                    disabled=not can_edit_cust,
                )
                if st.button("Update Membership", key="btn_update_mem", disabled=not can_edit_cust):
                    update_customer_membership(selected_cid, new_mem)
                    st.success("Membership updated!")
                    st.rerun()

                st.markdown("### 📝 Internal Admin Notes")
                notes_val = st.text_area(
                    "Customer Notes",
                    value=cust_data.get("notes", ""),
                    key="admin_notes_edit",
                    disabled=not can_edit_cust,
                )
                if st.button("Save Customer Notes", key="btn_save_cnotes", disabled=not can_edit_cust):
                    update_customer_notes(selected_cid, notes_val)
                    st.success("Customer notes saved!")
                    st.rerun()

            with cp_col2:
                st.markdown("### 🧠 Agent Long-Term Memories Saved")
                mems = memory_mgr.get_all_user_memories(selected_cid)
                if mems:
                    for i, m in enumerate(mems, 1):
                        st.markdown(f"**{i}.** {m}")
                else:
                    st.info("No long-term memories extracted for this customer yet.")

                st.divider()

                st.markdown("### 🎫 Customer Support Ticket History")
                c_tickets = [t for t in tickets if t.get("customer_id") == selected_cid]
                if c_tickets:
                    for ct in c_tickets:
                        st.caption(f"• `{ct.get('ticket_id')}` [{ct.get('status')}] - {ct.get('category')}: {ct.get('description')[:50]}...")
                else:
                    st.info("No support tickets filed for this customer.")

    # ---------------------------------------------------------------------------
    # Tab 3: Order Oversight & Fulfillment
    # ---------------------------------------------------------------------------
    with admin_tabs[2]:
        st.subheader("📦 System-Wide Orders Oversight")

        o_search = st.text_input("🔍 Search Orders by Order ID or Customer ID", key="admin_order_search")
        filtered_orders = orders

        if o_search:
            osq = o_search.lower()
            filtered_orders = {
                oid: o for oid, o in orders.items()
                if osq in oid.lower() or osq in o.get("customer_id", "").lower() or osq in o.get("product", "").lower()
            }

        st.caption(f"Displaying {len(filtered_orders)} orders")

        can_update_orders = has_permission(user_role, PERM_UPDATE_ORDERS)

        for oid, order in filtered_orders.items():
            o_status = order.get("order_status", "Processing")
            o_cust = order.get("customer_id")
            o_prod = order.get("product")
            o_amt = order.get("amount")
            o_carrier = order.get("carrier") or ""
            o_tracking = order.get("tracking_id") or ""
            o_date = order.get("order_date")

            with st.expander(f"📦 Order `{oid}` - {o_prod} (₹{o_amt:,}) | Status: {o_status}"):
                ocol1, ocol2 = st.columns(2)

                with ocol1:
                    st.markdown(f"**Order ID:** `{oid}`")
                    st.markdown(f"**Customer ID:** `{o_cust}`")
                    st.markdown(f"**Category:** `{order.get('category')}`")
                    st.markdown(f"**Payment Method:** `{order.get('payment_method')}` ({order.get('payment_status')})")
                    st.markdown(f"**Order Date:** `{o_date}`")

                with ocol2:
                    st.markdown("### 🚚 Update Fulfillment Status")
                    new_o_status = st.selectbox(
                        "Order Status",
                        ["Processing", "Shipped", "Delivered", "Return Requested", "Cancelled"],
                        index=["Processing", "Shipped", "Delivered", "Return Requested", "Cancelled"].index(o_status) if o_status in ["Processing", "Shipped", "Delivered", "Return Requested", "Cancelled"] else 0,
                        key=f"o_stat_{oid}",
                        disabled=not can_update_orders,
                    )

                    new_carrier = st.text_input(
                        "Shipping Carrier",
                        value=o_carrier,
                        placeholder="e.g. BlueDart Express",
                        key=f"o_carr_{oid}",
                        disabled=not can_update_orders,
                    )

                    new_tracking = st.text_input(
                        "Tracking ID",
                        value=o_tracking,
                        placeholder="e.g. TRK10009",
                        key=f"o_trk_{oid}",
                        disabled=not can_update_orders,
                    )

                    if st.button("💾 Update Order Status", key=f"o_btn_{oid}", disabled=not can_update_orders):
                        update_order_status(
                            order_id=oid,
                            status=new_o_status,
                            carrier=new_carrier,
                            tracking_id=new_tracking,
                        )
                        st.success(f"Order {oid} status updated!")
                        st.rerun()

    # ---------------------------------------------------------------------------
    # Tab 4: PostgreSQL & Vector DB Management
    # ---------------------------------------------------------------------------
    with admin_tabs[3]:
        st.subheader("🐘 PostgreSQL Database & 🎯 Vector DB Management")
        st.caption("Inspect PostgreSQL connection status, table records, trigger data migration, and re-index vector embeddings.")

        conn_info = check_connection_status()

        pg_col1, pg_col2 = st.columns([1, 1])

        with pg_col1:
            st.markdown("### 🔌 Database Connection Status")
            if conn_info["available"]:
                st.success(f"✅ **PostgreSQL Active** (`{conn_info['connection_url']}`)")
            else:
                st.warning(f"⚠️ **SQLite / JSON Fallback Active**\n\n*Connection URL:* `{conn_info['connection_url']}`\n\n*To enable PostgreSQL, set `POSTGRES_URL` in your `.env` file.*")

            st.divider()

            st.markdown("### 🛠️ Database Actions & Seeding")
            if st.button("🔄 Trigger PostgreSQL Table Migration & JSON Seed", use_container_width=True):
                with st.spinner("Initializing tables and seeding JSON data into PostgreSQL..."):
                    res = init_db_and_seed()
                    if res.get("status") == "success":
                        st.success(f"Successfully seeded PostgreSQL! Summary: `{res.get('seeded')}`")
                    elif res.get("status") == "skipped":
                        st.info(f"Skipped PostgreSQL seeding: {res.get('reason')}")
                    else:
                        st.error(f"PostgreSQL migration error: {res.get('error')}")

            if st.button("🎯 Re-Index Knowledge Base Vectors", use_container_width=True):
                with st.spinner("Generating document chunk vector embeddings..."):
                    res = reindex_knowledge_base()
                    if res.get("status") == "success":
                        st.success(f"Successfully indexed {res.get('total_chunks_indexed')} chunks across {res.get('postgres_vectors_synced')} PostgreSQL vector rows!")
                    else:
                        st.error(f"Vector indexing result: {res}")

        with pg_col2:
            st.markdown("### 📊 PostgreSQL Table Record Counts")
            counts = get_table_counts()
            if counts:
                for tbl, cnt in counts.items():
                    st.markdown(f"- **`{tbl}`**: `{cnt}` records")
            else:
                st.info("No PostgreSQL table statistics available (Fallback mode active).")

        st.divider()

        st.markdown("### 🔍 Vector Semantic Search Playground")
        st.caption("Interactively test cosine-similarity semantic vector retrieval across knowledge base documents.")

        v_col1, v_col2 = st.columns([3, 1])
        with v_col1:
            v_query = st.text_input(
                "Search Query",
                value="What happens if my package arrives damaged or defective?",
                placeholder="Type any natural language customer support question...",
                key="v_query_input"
            )
        with v_col2:
            v_top_k = st.slider("Top K Results", min_value=1, max_value=5, value=3, key="v_top_k_slider")

        if st.button("🚀 Search Vector Database", use_container_width=True):
            with st.spinner("Computing query vector embedding and searching vector store..."):
                v_results = search_knowledge_vectors(v_query, top_k=v_top_k)
                if not v_results:
                    st.warning("No relevant vector matches found. Try clicking 'Re-Index Knowledge Base Vectors' above.")
                else:
                    for i, r in enumerate(v_results, 1):
                        score_pct = int(r.get("similarity_score", 0) * 100)
                        st.markdown(f"#### Match #{i}: Document `{r.get('filename')}` (Similarity: **{score_pct}%**) - Engine: `{r.get('source')}`")
                        st.info(r.get("content"))

    # ---------------------------------------------------------------------------
    # Tab 5: User Role Access Control (Admin Restricted)
    # ---------------------------------------------------------------------------
    if has_permission(user_role, PERM_MANAGE_ROLES):
        with admin_tabs[4]:
            st.subheader("🔑 Role-Based Access Control (RBAC) Management")
            st.caption("Assign user roles across System Admin, Support Agent, Auditor, and Customer profiles.")

            users_db = load_users()

            for uname, udata in users_db.items():
                rcol1, rcol2, rcol3 = st.columns([2, 2, 2])

                with rcol1:
                    st.markdown(f"**Username:** `{uname}`")
                    st.markdown(f"**Name:** {udata.get('name')}")
                    st.markdown(f"**Email:** {udata.get('email')}")

                with rcol2:
                    current_r = udata.get("role", "customer")
                    selected_role = st.selectbox(
                        "Assigned Role",
                        ["admin", "agent", "auditor", "customer"],
                        index=["admin", "agent", "auditor", "customer"].index(current_r),
                        key=f"role_sel_{uname}",
                    )

                with rcol3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Update User Role 🔑", key=f"btn_role_{uname}", use_container_width=True):
                        update_user_role(uname, selected_role)
                        st.success(f"Role for '{uname}' updated to {selected_role.upper()}!")
                        st.rerun()

