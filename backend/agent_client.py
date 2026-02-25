import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
AGENT_ID = os.getenv("ELASTIC_AGENT_ID", "afrigov-sentinel")
KIBANA_URL = os.getenv("KIBANA_URL")

AGENT_ENDPOINT = f"{KIBANA_URL}/api/agent_builder/converse"


def build_prompt(incident: dict) -> str:
    return f"""Analyse cet incident :
Description: {incident.get('description', '')}
Service: {incident.get('service', '')}
Catégorie: {incident.get('category', '')}
Sévérité: {incident.get('severity', '')}/5
Ville: {incident.get('ville', '')}
Région: {incident.get('region', '')}
Priorité: {incident.get('priority', '')}
Signalé par: {incident.get('reporter_type', '')}

Suis tes 3 étapes obligatoires (Search, ES|QL, Décision) et retourne uniquement le JSON de décision."""


async def analyze_incident(incident: dict, similar_incidents: list = None) -> dict:
    """Call Elastic Agent Builder /converse endpoint."""
    prompt = build_prompt(incident)

    headers = {
        "Authorization": f"ApiKey {ELASTIC_API_KEY}",
        "Content-Type": "application/json",
        "kbn-xsrf": "true",
    }

    payload = {
        "input": prompt,
        "agent_id": AGENT_ID,
    }

    content = ""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(AGENT_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # ✅ Real response structure:
        # data["response"]["message"] = "```json\n{...}\n```"
        response_obj = data.get("response", {})
        if isinstance(response_obj, dict):
            content = response_obj.get("message", "")
        elif isinstance(response_obj, str):
            content = response_obj
        else:
            content = str(response_obj)

        print(f"[AgentClient] Raw content: {content[:200]}")

        content = _clean_json(content)
        result = json.loads(content)

        return {
            "risk_score": float(result.get("risk_score", 2.0)),
            "decision": result.get("decision", "STANDARD_PROCESSING"),
            "explanation": result.get("explanation", ""),
            "action_plan": result.get("action_plan", []),
            "context": result.get("context", {}),
        }

    except httpx.HTTPStatusError as e:
        print(f"[AgentClient] HTTP {e.response.status_code}: {e.response.text[:500]}")
        return _fallback_decision(incident)
    except json.JSONDecodeError as e:
        print(f"[AgentClient] JSON parse error: {e} — content: {content[:300]}")
        return _fallback_decision(incident)
    except Exception as e:
        print(f"[AgentClient] Error: {type(e).__name__}: {e}")
        return _fallback_decision(incident)


def _clean_json(content: str) -> str:
    """Extract JSON object from agent response."""
    if not isinstance(content, str):
        content = str(content)
    content = content.strip()
    # Remove markdown code blocks
    if "```" in content:
        parts = content.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                return part
    # Find raw JSON object
    start = content.find("{")
    end = content.rfind("}") + 1
    if start != -1 and end > start:
        return content[start:end]
    return content


def _fallback_decision(incident: dict) -> dict:
    severity = incident.get("severity", 1)
    mapping = {
        5: ("CRITICAL_ESCALATION", 4.5),
        4: ("URGENT_ACTION", 3.5),
        3: ("STANDARD_PROCESSING", 2.5),
        2: ("MONITOR", 1.5),
        1: ("MONITOR", 1.0),
    }
    decision, score = mapping.get(severity, ("MONITOR", 1.0))
    return {
        "risk_score": score,
        "decision": decision,
        "explanation": "Analyse de secours basée sur la sévérité (agent IA indisponible).",
        "action_plan": [
            "Vérifier l'incident manuellement",
            "Contacter le service responsable",
            "Mettre à jour le statut",
        ],
        "context": {},
    }