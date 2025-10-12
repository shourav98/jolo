import os
from django.conf import settings

try:
    from twilio.rest import Client
except Exception:
    Client = None

def _client():
    if Client is None:
        return None
    sid = os.getenv("TWILIO_ACCOUNT_SID") or getattr(settings, "TWILIO_ACCOUNT_SID", None)
    tok = os.getenv("TWILIO_AUTH_TOKEN")  or getattr(settings, "TWILIO_AUTH_TOKEN", None)
    if not (sid and tok):
        return None
    return Client(sid, tok)

def send_sms(to_phone: str, body: str) -> bool:
    client = _client()
    if not client:
        return False
    sender = os.getenv("TWILIO_SMS_FROM") or getattr(settings, "TWILIO_SMS_FROM", None)
    if not sender:
        return False
    client.messages.create(to=to_phone, from_=sender, body=body)
    return True

def send_whatsapp(to_phone: str, body: str) -> bool:
    client = _client()
    if not client:
        return False
    from_wa = os.getenv("TWILIO_WA_FROM") or getattr(settings, "TWILIO_WA_FROM", None)
    if not from_wa:
        return False
    to = to_phone if str(to_phone).startswith("whatsapp:") else f"whatsapp:{to_phone}"
    client.messages.create(body=body, from_=from_wa, to=to)
    return True
