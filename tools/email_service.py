import json
import os
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Any, Optional

from tools.customer_lookup import get_customer_by_email
from tools.i18n import detect_language

EMAIL_INBOX_FILE = Path("data/email_inbox.json")


def get_smtp_config() -> Dict[str, Any]:
    """Retrieve SMTP configuration from environment variables."""
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USER", ""),
        "pass": os.getenv("SMTP_PASS", ""),
        "from_email": os.getenv("SMTP_FROM_EMAIL", os.getenv("SMTP_USER", "support@supportagent.com")),
        "is_configured": bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER")),
    }


def _load_emails() -> List[Dict[str, Any]]:
    if not EMAIL_INBOX_FILE.exists():
        EMAIL_INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Seed with initial demo email data
        demo_emails = [
            {
                "id": "EML-1001",
                "thread_id": "thr_rahul_s",
                "sender_email": "rahul.sharma@example.com",
                "sender_name": "Rahul Sharma",
                "recipient_email": "support@supportagent.com",
                "subject": "Inquiry regarding order ORD1001 shipping status",
                "body": "Hello Support Team,\n\nI ordered Wireless Noise-Canceling Headphones (ORD1001) last week. Can you please check when it will be delivered?\n\nThank you,\nRahul",
                "timestamp": datetime.now().isoformat(),
                "direction": "inbound",
                "status": "processed",
                "ai_auto_replied": True,
                "customer_id": "CUST001",
            },
            {
                "id": "EML-1002",
                "thread_id": "thr_rahul_s",
                "sender_email": "support@supportagent.com",
                "sender_name": "AI Support Agent",
                "recipient_email": "rahul.sharma@example.com",
                "subject": "Re: Inquiry regarding order ORD1001 shipping status",
                "body": "Hello Rahul,\n\nThank you for reaching out! Your order ORD1001 for Wireless Noise-Canceling Headphones is currently Shipped via FedEx (Tracking ID: FDX987654321). Estimated delivery date is 2026-03-08.\n\nPlease let us know if you need any further assistance!\n\nBest regards,\nAI Customer Support Team",
                "timestamp": datetime.now().isoformat(),
                "direction": "outbound",
                "status": "sent",
                "ai_auto_replied": True,
                "customer_id": "CUST001",
            }
        ]
        EMAIL_INBOX_FILE.write_text(json.dumps(demo_emails, indent=4), encoding="utf-8")
        return demo_emails

    try:
        return json.loads(EMAIL_INBOX_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_emails(emails: List[Dict[str, Any]]) -> None:
    EMAIL_INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
    EMAIL_INBOX_FILE.write_text(json.dumps(emails, indent=4), encoding="utf-8")


def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    thread_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    is_auto_reply: bool = False,
) -> Dict[str, Any]:
    """
    Send an email via SMTP if configured, and always record in email log store.
    """
    config = get_smtp_config()
    sender = from_email or config["from_email"]
    smtp_sent = False
    smtp_error = None

    if config["is_configured"]:
        try:
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(config["host"], config["port"], timeout=10)
            server.starttls()
            server.login(config["user"], config["pass"])
            server.send_message(msg)
            server.quit()
            smtp_sent = True
        except Exception as e:
            smtp_error = str(e)

    email_id = "EML-" + str(uuid.uuid4())[:8].upper()
    now_iso = datetime.now().isoformat()

    record = {
        "id": email_id,
        "thread_id": thread_id or f"thr_{to_email.replace('@', '_').replace('.', '_')}",
        "sender_email": sender,
        "sender_name": "AI Support Agent" if is_auto_reply else "Support Team",
        "recipient_email": to_email,
        "subject": subject,
        "body": body,
        "timestamp": now_iso,
        "direction": "outbound",
        "status": "sent" if (smtp_sent or not config["is_configured"]) else "failed",
        "smtp_sent": smtp_sent,
        "smtp_error": smtp_error,
        "ai_auto_replied": is_auto_reply,
        "customer_id": customer_id,
    }

    emails = _load_emails()
    emails.append(record)
    _save_emails(emails)

    return record


def process_incoming_email(
    sender_email: str,
    sender_name: str,
    subject: str,
    body: str,
    graph_agent: Any,
    memory_mgr: Any,
    auto_reply: bool = True,
) -> Dict[str, Any]:
    """
    Ingest incoming email inquiry, run it through the AI support graph,
    auto-generate reply email, and record full conversation.
    """
    email_id = "EML-" + str(uuid.uuid4())[:8].upper()
    now_iso = datetime.now().isoformat()
    thread_key = f"email_thr_{sender_email.strip().lower()}"

    # Match customer profile
    cust_profile = get_customer_by_email(sender_email)
    customer_id = cust_profile["customer_id"] if cust_profile else "CUST001"

    inbound_record = {
        "id": email_id,
        "thread_id": thread_key,
        "sender_email": sender_email,
        "sender_name": sender_name or sender_email.split("@")[0].capitalize(),
        "recipient_email": "support@supportagent.com",
        "subject": subject,
        "body": body,
        "timestamp": now_iso,
        "direction": "inbound",
        "status": "processed",
        "ai_auto_replied": False,
        "customer_id": customer_id,
    }

    emails = _load_emails()
    emails.append(inbound_record)
    _save_emails(emails)

    ai_response_text = ""
    outbound_record = None

    if auto_reply and graph_agent:
        input_msg = f"[Email Subject: {subject}]\n\n{body}"
        detected_lang = detect_language(body)
        config = {"configurable": {"thread_id": thread_key}}
        initial_state = {
            "messages": [{"role": "user", "content": input_msg}],
            "user_id": customer_id,
            "user_message": input_msg,
            "language": detected_lang,
        }

        try:
            res = graph_agent.invoke(initial_state, config=config)
            ai_response_text = res.get("response", "Thank you for contacting support. We have received your inquiry.")
            requires_human = res.get("requires_human", False)

            if requires_human:
                ai_response_text += "\n\n(Note: Your ticket has been flagged for human agent review.)"

            # Auto send reply email
            reply_subject = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
            outbound_record = send_email(
                to_email=sender_email,
                subject=reply_subject,
                body=ai_response_text,
                thread_id=thread_key,
                customer_id=customer_id,
                is_auto_reply=True,
            )

            # Update inbound status
            emails = _load_emails()
            for e in emails:
                if e["id"] == email_id:
                    e["status"] = "processed"
                    e["ai_auto_replied"] = True
                    break
            _save_emails(emails)

        except Exception as err:
            ai_response_text = f"We received your email, but encountered an issue generating automated reply: {err}"

    return {
        "inbound": inbound_record,
        "ai_response": ai_response_text,
        "outbound": outbound_record,
    }


def fetch_all_emails() -> List[Dict[str, Any]]:
    return _load_emails()


def clear_email_history() -> None:
    _save_emails([])
