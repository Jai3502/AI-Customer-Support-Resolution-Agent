import json
import streamlit as st
from datetime import datetime

from tools.email_service import (
    fetch_all_emails,
    send_email,
    process_incoming_email,
    get_smtp_config,
    clear_email_history,
)
from tools.whatsapp_service import (
    fetch_all_whatsapp_messages,
    send_whatsapp_message,
    process_incoming_whatsapp,
    get_whatsapp_config,
    clear_whatsapp_history,
)
from tools.customer_lookup import list_all_customers, get_customer_by_email, get_customer_by_phone


def render_omnichannel_view(graph_agent, memory_mgr):
    st.markdown("## 📡 Omnichannel Customer Support Hub")
    st.caption("Manage, test, and monitor automated Email and WhatsApp communication channels powered by AI.")

    smtp_cfg = get_smtp_config()
    wa_cfg = get_whatsapp_config()

    # ---------------------------------------------------------------------------
    # Channel Summary Metrics
    # ---------------------------------------------------------------------------
    emails = fetch_all_emails()
    wa_msgs = fetch_all_whatsapp_messages()

    inbound_emails = [e for e in emails if e.get("direction") == "inbound"]
    outbound_emails = [e for e in emails if e.get("direction") == "outbound"]
    inbound_wa = [w for w in wa_msgs if w.get("direction") == "inbound"]
    outbound_wa = [w for w in wa_msgs if w.get("direction") == "outbound"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📧 Total Emails Processed", len(emails), delta=f"{len(inbound_emails)} Inbound")
    with col2:
        st.metric("💬 WhatsApp Messages", len(wa_msgs), delta=f"{len(inbound_wa)} Inbound")
    with col3:
        email_status = "🟢 SMTP Live" if smtp_cfg["is_configured"] else "🟡 Sandbox Mode"
        st.metric("Email Channel", email_status)
    with col4:
        wa_status = f"🟢 {wa_cfg['provider'].upper()} Live" if wa_cfg["is_live"] else "🟡 Sandbox Mode"
        st.metric("WhatsApp Channel", wa_status)

    st.divider()

    # ---------------------------------------------------------------------------
    # Navigation Tabs
    # ---------------------------------------------------------------------------
    tab_email, tab_whatsapp, tab_settings = st.tabs([
        "📧 Email Operations Hub",
        "💬 WhatsApp Messaging Console",
        "⚙️ Channel Settings & Credentials"
    ])

    # ===========================================================================
    # TAB 1: Email Operations Hub
    # ===========================================================================
    with tab_email:
        sub_tab1, sub_tab2, sub_tab3 = st.tabs([
            "📬 Inbox & Log History",
            "📥 Inbound Email Simulator",
            "✉️ Compose Outbound Email"
        ])

        # Sub-tab 1: Inbox
        with sub_tab1:
            st.subheader("Email Communication Log")
            if not emails:
                st.info("No emails recorded yet in the system.")
            else:
                col_f1, col_f2 = st.columns([2, 2])
                with col_f1:
                    filter_dir = st.selectbox("Filter Direction", ["All", "Inbound (Received)", "Outbound (Sent)"], key="em_dir")
                with col_f2:
                    search_query = st.text_input("Search Email / Subject", "", key="em_search")

                filtered_emails = emails
                if filter_dir == "Inbound (Received)":
                    filtered_emails = [e for e in filtered_emails if e.get("direction") == "inbound"]
                elif filter_dir == "Outbound (Sent)":
                    filtered_emails = [e for e in filtered_emails if e.get("direction") == "outbound"]

                if search_query:
                    sq = search_query.lower()
                    filtered_emails = [
                        e for e in filtered_emails
                        if sq in e.get("sender_email", "").lower()
                        or sq in e.get("recipient_email", "").lower()
                        or sq in e.get("subject", "").lower()
                        or sq in e.get("body", "").lower()
                    ]

                st.caption(f"Showing {len(filtered_emails)} email record(s)")
                for eml in reversed(filtered_emails):
                    is_inbound = eml.get("direction") == "inbound"
                    badge = "📥 INBOUND" if is_inbound else "📤 OUTBOUND"
                    badge_color = "#3b82f6" if is_inbound else "#10b981"
                    ai_badge = " | 🤖 AI Auto-Replied" if eml.get("ai_auto_replied") else ""

                    with st.expander(f"{badge} | **{eml.get('subject')}** — {eml.get('sender_name')} ({eml.get('timestamp')[:19]})"):
                        st.markdown(f"**From:** `{eml.get('sender_email')}`  ")
                        st.markdown(f"**To:** `{eml.get('recipient_email')}`  ")
                        st.markdown(f"**Customer ID:** `{eml.get('customer_id', 'N/A')}` {ai_badge}")
                        st.markdown("**Message Content:**")
                        st.text_area("Body", eml.get("body", ""), height=120, disabled=True, key=f"em_body_{eml.get('id')}")

        # Sub-tab 2: Inbound Simulator
        with sub_tab2:
            st.subheader("Simulate Incoming Customer Email")
            st.caption("Test how the AI Support Agent processes customer emails, matches customer data, and sends an automated reply.")

            customers = list_all_customers()
            cust_options = ["Custom Sender Email..."] + [f"{c['name']} ({c['email']})" for cid, c in customers.items()]
            selected_cust = st.selectbox("Select Existing Customer Profile or Custom", cust_options, key="sim_cust_sel")

            if selected_cust != "Custom Sender Email...":
                selected_cid = [cid for cid, c in customers.items() if f"{c['name']} ({c['email']})" == selected_cust][0]
                cdata = customers[selected_cid]
                default_email = cdata["email"]
                default_name = cdata["name"]
            else:
                default_email = "customer@example.com"
                default_name = "Jane Doe"

            with st.form("inbound_email_form"):
                sim_email = st.text_input("Sender Email Address", value=default_email)
                sim_name = st.text_input("Sender Full Name", value=default_name)
                sim_subject = st.text_input("Email Subject", value="Inquiry regarding my recent order delivery")
                sim_body = st.text_area("Email Content / Question", value="Hi Support Team,\n\nI ordered headphones (ORD1001) last week. Could you please confirm the tracking status and delivery date?\n\nThanks,\nSarah", height=140)
                sim_auto_reply = st.checkbox("Trigger AI Auto-Responder & Send Email Reply", value=True)

                submit_sim = st.form_submit_button("📥 Send Email to AI Agent & Process", type="primary", use_container_width=True)

            if submit_sim:
                if not sim_email or not sim_body:
                    st.error("Please enter a valid email address and email content.")
                else:
                    with st.spinner("Processing incoming email through AI Support Graph..."):
                        result = process_incoming_email(
                            sender_email=sim_email,
                            sender_name=sim_name,
                            subject=sim_subject,
                            body=sim_body,
                            graph_agent=graph_agent,
                            memory_mgr=memory_mgr,
                            auto_reply=sim_auto_reply,
                        )

                    st.success("✅ Email received and processed successfully!")
                    
                    st.markdown("### 🔍 Pipeline Processing Results")
                    col_res1, col_res2 = st.columns(2)
                    with col_res1:
                        st.markdown("**📥 Received Email Record**")
                        st.json(result["inbound"])
                    with col_res2:
                        st.markdown("**🤖 AI Auto-Generated Response**")
                        st.info(result.get("ai_response", "No AI response generated."))

                    st.rerun()

        # Sub-tab 3: Compose Outbound
        with sub_tab3:
            st.subheader("Compose & Send Email")
            st.caption("Send a manual email directly to a customer.")

            with st.form("compose_email_form"):
                to_addr = st.text_input("Recipient Email (To:)", value="sarah.c@techcorp.com")
                out_subject = st.text_input("Subject", value="Update regarding your support inquiry")
                out_body = st.text_area("Message Body", value="Dear Customer,\n\nWe have updated your ticket status...\n\nBest regards,\nCustomer Support Team", height=150)
                submit_out = st.form_submit_button("📤 Send Email", type="primary", use_container_width=True)

            if submit_out:
                if not to_addr or not out_body:
                    st.error("Recipient email and message body are required.")
                else:
                    res = send_email(
                        to_email=to_addr,
                        subject=out_subject,
                        body=out_body,
                        is_auto_reply=False,
                    )
                    st.success(f"✅ Email sent successfully! (Record ID: {res['id']})")
                    if res.get("smtp_sent"):
                        st.info("Sent via live SMTP server.")
                    else:
                        st.warning("Logged in Sandbox mode (SMTP not configured or failed).")
                    st.rerun()

    # ===========================================================================
    # TAB 2: WhatsApp Messaging Console
    # ===========================================================================
    with tab_whatsapp:
        sub_wa1, sub_wa2, sub_wa3 = st.tabs([
            "💬 WhatsApp Chat Console",
            "📱 Interactive WhatsApp Simulator",
            "🔌 Webhook Payload Inspector"
        ])

        # Sub-tab 1: WhatsApp Chat Logs
        with sub_wa1:
            st.subheader("WhatsApp Conversation Logs")
            if not wa_msgs:
                st.info("No WhatsApp messages recorded yet.")
            else:
                threads = {}
                for m in wa_msgs:
                    th = m.get("thread_id", "default")
                    if th not in threads:
                        threads[th] = []
                    threads[th].append(m)

                st.caption(f"Active Conversation Threads: {len(threads)}")
                for th_id, msgs in threads.items():
                    sample_sender = msgs[0].get("sender_name") or msgs[0].get("sender_phone")
                    with st.expander(f"💬 Thread: {sample_sender} ({len(msgs)} messages)"):
                        for msg in msgs:
                            is_inbound = msg.get("direction") == "inbound"
                            align = "left" if is_inbound else "right"
                            bg_color = "#1e293b" if is_inbound else "#065f46"
                            icon = "👤" if is_inbound else "🤖"
                            sender_label = msg.get("sender_name") or msg.get("sender_phone")

                            st.markdown(
                                f"""
                                <div style="background-color: {bg_color}; padding: 10px 14px; border-radius: 12px; margin-bottom: 8px; max-width: 85%; margin-left: {'0' if is_inbound else 'auto'};">
                                    <span style="font-size: 0.8rem; color: #94a3b8;">{icon} <b>{sender_label}</b> • {msg.get('timestamp')[:19]}</span>
                                    <div style="margin-top: 4px; font-size: 0.95rem; color: #f8fafc;">{msg.get('message')}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

        # Sub-tab 2: WhatsApp Simulator
        with sub_wa2:
            st.subheader("Interactive WhatsApp Simulator")
            st.caption("Simulate a customer sending a WhatsApp message to your AI Support Agent in real-time.")

            customers = list_all_customers()
            cust_phone_options = ["Custom Phone Number..."] + [f"{c['name']} ({c.get('phone', 'No Phone')})" for cid, c in customers.items()]
            selected_wa_cust = st.selectbox("Select Customer Profile", cust_phone_options, key="sim_wa_cust_sel")

            if selected_wa_cust != "Custom Phone Number...":
                selected_cid = [cid for cid, c in customers.items() if f"{c['name']} ({c.get('phone', 'No Phone')})" == selected_wa_cust][0]
                cdata = customers[selected_cid]
                default_phone = cdata.get("phone") or "+1-555-0199"
                default_wa_name = cdata["name"]
            else:
                default_phone = "+1-555-0199"
                default_wa_name = "Sarah Connor"

            with st.form("wa_simulator_form"):
                sim_phone = st.text_input("Customer Phone Number", value=default_phone)
                sim_wa_sender_name = st.text_input("Customer Name", value=default_wa_name)
                sim_wa_msg = st.text_area("WhatsApp Message Text", value="Hi! What is your return policy for open box items?", height=100)
                sim_wa_reply = st.checkbox("Enable AI Auto-Responder over WhatsApp", value=True)

                submit_wa_sim = st.form_submit_button("💬 Send WhatsApp Message & Trigger AI", type="primary", use_container_width=True)

            if submit_wa_sim:
                if not sim_phone or not sim_wa_msg:
                    st.error("Please enter both phone number and message.")
                else:
                    with st.spinner("Processing WhatsApp message through AI Agent..."):
                        wa_result = process_incoming_whatsapp(
                            from_phone=sim_phone,
                            message_text=sim_wa_msg,
                            sender_name=sim_wa_sender_name,
                            graph_agent=graph_agent,
                            memory_mgr=memory_mgr,
                            auto_reply=sim_wa_reply,
                        )

                    st.success("✅ WhatsApp message received and AI response dispatched!")
                    
                    st.markdown("### 💬 Chat Preview")
                    col_wa_res1, col_wa_res2 = st.columns(2)
                    with col_wa_res1:
                        st.markdown("**📥 Inbound Customer Message**")
                        st.json(wa_result["inbound"])
                    with col_wa_res2:
                        st.markdown("**🤖 AI WhatsApp Auto-Reply**")
                        st.info(wa_result.get("ai_response", "No AI response generated."))

                    st.rerun()

        # Sub-tab 3: Webhook Inspector
        with sub_wa3:
            st.subheader("WhatsApp Webhook Payload Inspector")
            st.caption("Sample HTTP POST payloads for integrating real WhatsApp Webhooks (Twilio / Meta).")

            col_wh1, col_wh2 = st.columns(2)
            with col_wh1:
                st.markdown("#### Twilio WhatsApp Webhook Format")
                st.code(
                    """POST /api/webhooks/whatsapp HTTP/1.1
Host: your-domain.com
Content-Type: application/x-www-form-urlencoded

SmsMessageSid=SMxxxxxx
&NumMedia=0
&ProfileName=Sarah+Connor
&MessageType=text
&From=whatsapp%3A%2B15550199
&To=whatsapp%3A%2B14155238886
&Body=What+is+my+order+status%3F""",
                    language="http",
                )

            with col_wh2:
                st.markdown("#### Meta Cloud API Webhook Format")
                st.code(
                    """POST /api/webhooks/whatsapp HTTP/1.1
Host: your-domain.com
Content-Type: application/json

{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "15550199",
          "id": "wamid.HBgL...",
          "text": { "body": "What is my order status?" }
        }]
      }
    }]
  }]
}""",
                    language="json",
                )

    # ===========================================================================
    # TAB 3: Settings & Credentials
    # ===========================================================================
    with tab_settings:
        st.subheader("⚙️ Channel Credentials & Integration Settings")

        col_st1, col_st2 = st.columns(2)
        with col_st1:
            st.markdown("### 📧 SMTP / IMAP Email Setup")
            st.markdown("""
            Configure email server credentials in your `.env` file to send live emails:
            ```env
            SMTP_HOST=smtp.gmail.com
            SMTP_PORT=587
            SMTP_USER=your-email@gmail.com
            SMTP_PASS=your-app-password
            SMTP_FROM_EMAIL=support@yourdomain.com
            ```
            """)

            if smtp_cfg["is_configured"]:
                st.success("🟢 SMTP is configured! Live emails will be sent.")
            else:
                st.warning("🟡 SMTP credentials not detected. Operating in local Sandbox Mode.")

            if st.button("🔴 Clear Email History Log"):
                clear_email_history()
                st.success("Cleared all email records.")
                st.rerun()

        with col_st2:
            st.markdown("### 💬 Twilio / Meta WhatsApp Setup")
            st.markdown("""
            Configure Twilio or Meta API keys in `.env` to enable live WhatsApp messaging:
            ```env
            # Twilio WhatsApp Setup
            TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxx
            TWILIO_AUTH_TOKEN=your_auth_token
            TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

            # OR Meta Cloud API Setup
            META_WHATSAPP_TOKEN=EAAG...
            META_WHATSAPP_PHONE_NUMBER_ID=109...
            ```
            """)

            if wa_cfg["is_live"]:
                st.success(f"🟢 {wa_cfg['provider'].upper()} WhatsApp API is configured! Live messaging active.")
            else:
                st.warning("🟡 WhatsApp API keys not detected. Operating in local Sandbox Mode.")

            if st.button("🔴 Clear WhatsApp Message Log"):
                clear_whatsapp_history()
                st.success("Cleared all WhatsApp records.")
                st.rerun()
