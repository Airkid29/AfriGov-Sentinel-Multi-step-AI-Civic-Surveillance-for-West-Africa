import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_TO = os.getenv("TWILIO_WHATSAPP_TO", "")  # Authority's WhatsApp number

TWILIO_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"

ENABLED = bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_TO)


async def send_critical_alert(incident: dict, analysis: dict) -> bool:
    """Send WhatsApp alert to authority when CRITICAL_ESCALATION is triggered."""
    if not ENABLED:
        print("[WhatsApp] Not configured — skipping alert")
        return False

    contact = analysis.get("contact", {})
    responsable = contact.get("responsable", "Responsable concerné")
    tel = contact.get("telephone", "N/A")

    message = (
        f"🚨 *AfriGov Sentinel — CRITICAL ESCALATION*\n\n"
        f"*Incident:* {incident.get('incident_id', 'N/A')}\n"
        f"*Service:* {incident.get('service', 'N/A')}\n"
        f"*Ville:* {incident.get('ville', 'N/A')} ({incident.get('region', 'N/A')})\n"
        f"*Sévérité:* {incident.get('severity', 'N/A')}/5\n"
        f"*Risk Score:* {analysis.get('risk_score', 'N/A')}/5.0\n\n"
        f"*Description:*\n{incident.get('description', '')[:200]}\n\n"
        f"*Responsable identifié:* {responsable}\n"
        f"*Contact:* {tel}\n\n"
        f"*Plan d'action:*\n" +
        "\n".join([f"→ {a}" for a in analysis.get("action_plan", [])[:3]]) +
        f"\n\n_Gérez cet incident sur:_\nhttps://afrigov-sentinel.netlify.app"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                TWILIO_URL,
                data={"From": TWILIO_FROM, "To": f"whatsapp:{TWILIO_TO}", "Body": message},
                auth=(TWILIO_SID, TWILIO_TOKEN),
            )
            if resp.status_code == 201:
                print(f"[WhatsApp] ✅ Alert sent for {incident.get('incident_id')}")
                return True
            else:
                print(f"[WhatsApp] ❌ Failed: {resp.status_code} {resp.text[:200]}")
                return False
    except Exception as e:
        print(f"[WhatsApp] Error: {e}")
        return False