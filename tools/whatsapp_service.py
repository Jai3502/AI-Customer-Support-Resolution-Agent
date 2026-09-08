import json
import os
import urllib.request
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from tools.customer_lookup import get_customer_by_phone

WHATSAPP_FILE = Path("data/whatsapp_messages.json")


def get_whatsapp_config() -> Dict[str, Any]:
    """Retrieve WhatsApp Twilio / Meta Cloud API configuration."""
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_num = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    meta_token = os.getenv("META_WHATSAPP_TOKEN", "")
    meta_phone_id = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID", "")

    provider = "sandbox"
    if twilio_sid and twilio_token:
        provider = "twilio"
    elif meta_token and meta_phone_id:
        provider = "meta"

    return {
        "provider": provider,
        "twilio_sid": twilio_sid,
        "twilio_number": twilio_num,
        "meta_phone_id": meta_phone_id,
        "is_live": provider in ["twilio", "meta"],
    }


def _load_whatsapp_messages() -> List[Dict[str, Any]]:
    if not WHATSAPP_FILE.exists():
        WHATSAPP_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Initial demo seed
        demo_msgs = [
            {
                "id": "WA-1001",
                "thread_id": "wa_thr_919876543210",
                "sender_phone": "+91-9876543210",
                "sender_name": "Rahul Sharma",
                "recipient_phone": "whatsapp:+14155238886",
                "message": "Hi, can I return my Wireless Noise-Canceling Headphones if I opened the box?",
                "timestamp": datetime.now().isoformat(),
                "direction": "inbound",
                "status": "processed",
                "ai_auto_replied": True,
                "customer_id": "CUST001",
            },
            {
                "id": "WA-1002",
                "thread_id": "wa_thr_919876543210",
                "sender_phone": "whatsapp:+14155238886",
                "sender_name": "AI Support Bot",
                "recipient_phone": "+91-9876543210",
                "message": "Hello Rahul! Yes, under our 30-day return policy, items can be returned within 30 days of delivery. As long as all original accessories are included, you are eligible for a full refund or replacement. Would you like me to initiate a return ticket for you?",
                "timestamp": datetime.now().isoformat(),
                "direction": "outbound",
                "status": "sent",
                "ai_auto_replied": True,
                "customer_id": "CUST001",
            }
        ]
        WHATSAPP_FILE.write_text(json.dumps(demo_msgs, indent=4), encoding="utf-8")
        return demo_msgs

    try:
        return json.loads(WHATSAPP_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_whatsapp_messages(msgs: List[Dict[str, Any]]) -> None:
    WHATSAPP_FILE.parent.mkdir(parents=True, exist_ok=True)
    WHATSAPP_FILE.write_text(json.dumps(msgs, indent=4), encoding="utf-8")


def send_whatsapp_message(
    to_phone: str,
    message_text: str,
    from_phone: Optional[str] = None,
    thread_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    is_auto_reply: bool = False,
) -> Dict[str, Any]:
    """
    Send WhatsApp message via Twilio/Meta API if configured, and save to message log.
    """
    config = get_whatsapp_config()
    sender = from_phone or config["twilio_number"]
    api_sent = False
    api_error = None

    # Twilio API Execution
    if config["provider"] == "twilio":
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{config['twilio_sid']}/Messages.json"
            formatted_to = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
            formatted_from = sender if sender.startswith("whatsapp:") else f"whatsapp:{sender}"

            data = urllib.parse.urlencode({
                "To": formatted_to,
                "From": formatted_from,
                "Body": message_text,
            }).encode("utf-8")

            req = urllib.request.Request(url, data=data, method="POST")
            # Basic auth
            import base64
            auth_str = f"{config['twilio_sid']}:{os.getenv('TWILIO_AUTH_TOKEN', '')}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
            req.add_header("Authorization", f"Basic {b64_auth}")

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    api_sent = True
        except Exception as e:
            api_error = str(e)

    # Meta Cloud API Execution
    elif config["provider"] == "meta":
        try:
            url = f"https://graph.facebook.com/v18.0/{config['meta_phone_id']}/messages"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to_phone.replace("+", "").replace("whatsapp:", "").strip(),
                "type": "text",
                "text": {"preview_url": False, "body": message_text},
            }).encode("utf-8")

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Authorization", f"Bearer {os.getenv('META_WHATSAPP_TOKEN', '')}")
            req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status in (200, 201):
                    api_sent = True
        except Exception as e:
            api_error = str(e)

    msg_id = "WA-" + str(uuid.uuid4())[:8].upper()
    now_iso = datetime.now().isoformat()
    clean_phone = "".join(c for c in to_phone if c.isdigit())

    record = {
        "id": msg_id,
        "thread_id": thread_id or f"wa_thr_{clean_phone}",
        "sender_phone": sender,
        "sender_name": "AI Support Bot" if is_auto_reply else "Support Agent",
        "recipient_phone": to_phone,
        "message": message_text,
        "timestamp": now_iso,
        "direction": "outbound",
        "status": "sent" if (api_sent or not config["is_live"]) else "failed",
        "api_sent": api_sent,
        "api_error": api_error,
        "ai_auto_replied": is_auto_reply,
        "customer_id": customer_id,
    }

    msgs = _load_whatsapp_messages()
    msgs.append(record)
    _save_whatsapp_messages(msgs)

    return record


def process_incoming_whatsapp(
    from_phone: str,
    message_text: str,
    sender_name: Optional[str] = None,
    graph_agent: Any = None,
    memory_mgr: Any = None,
    auto_reply: bool = True,
) -> Dict[str, Any]:
    """
    Ingest incoming WhatsApp message, resolve customer by phone number,
    run through AI agent pipeline, auto-respond via WhatsApp, and record log.
    """
    msg_id = "WA-" + str(uuid.uuid4())[:8].upper()
    now_iso = datetime.now().isoformat()
    clean_phone = "".join(c for c in from_phone if c.isdigit())
    thread_key = f"wa_thr_{clean_phone}"

    # Match customer by phone number
    cust_profile = get_customer_by_phone(from_phone)
    customer_id = cust_profile["customer_id"] if cust_profile else "CUST001"
    resolved_name = sender_name or (cust_profile.get("name") if cust_profile else f"Customer ({from_phone})")

    inbound_record = {
        "id": msg_id,
        "thread_id": thread_key,
        "sender_phone": from_phone,
        "sender_name": resolved_name,
        "recipient_phone": "whatsapp:+14155238886",
        "message": message_text,
        "timestamp": now_iso,
        "direction": "inbound",
        "status": "received",
        "ai_auto_replied": False,
        "customer_id": customer_id,
    }

    msgs = _load_whatsapp_messages()
    msgs.append(inbound_record)
    _save_whatsapp_messages(msgs)

    ai_response_text = ""
    outbound_record = None

    if auto_reply and graph_agent:
        config = {"configurable": {"thread_id": thread_key}}
        initial_state = {
            "messages": [{"role": "user", "content": message_text}],
            "user_id": customer_id,
            "user_message": message_text,
        }

        try:
            res = graph_agent.invoke(initial_state, config=config)
            ai_response_text = res.get("response", "Thank you for reaching out via WhatsApp. We received your message.")
            requires_human = res.get("requires_human", False)

            if requires_human:
                ai_response_text += "\n\n⚠️ Note: Your inquiry has been escalated to a human agent support representative."

            # Auto send reply over WhatsApp
            outbound_record = send_whatsapp_message(
                to_phone=from_phone,
                message_text=ai_response_text,
                thread_id=thread_key,
                customer_id=customer_id,
                is_auto_reply=True,
            )

            # Update inbound status
            msgs = _load_whatsapp_messages()
            for m in msgs:
                if m["id"] == msg_id:
                    m["status"] = "processed"
                    m["ai_auto_replied"] = True
                    break
            _save_whatsapp_messages(msgs)

        except Exception as err:
            ai_response_text = f"Received your WhatsApp message, but failed to generate AI response: {err}"

    return {
        "inbound": inbound_record,
        "ai_response": ai_response_text,
        "outbound": outbound_record,
    }


def fetch_all_whatsapp_messages() -> List[Dict[str, Any]]:
    return _load_whatsapp_messages()


def clear_whatsapp_history() -> None:
    _save_whatsapp_messages([])
