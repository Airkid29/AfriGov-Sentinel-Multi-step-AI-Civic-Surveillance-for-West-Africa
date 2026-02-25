from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from elastic_client import (
    check_connection, create_indices, index_incident,
    get_similar_incidents, log_decision, get_all_incidents,
    get_stats, es, INDEX_INCIDENTS, INDEX_DECISIONS
)
from agent_client import analyze_incident

app = FastAPI(title="AfriGov Sentinel API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class IncidentReport(BaseModel):
    description: str
    service: str
    category: str
    severity: int
    ville: str
    region: str
    reporter_type: Optional[str] = "Citoyen"
    lat: Optional[float] = None
    lon: Optional[float] = None

class StatusUpdate(BaseModel):
    status: str
    note: Optional[str] = ""

@app.on_event("startup")
async def startup_event():
    try:
        create_indices()
        # Create escalations index
        if not es.indices.exists(index="escalations"):
            es.indices.create(index="escalations", body={
                "mappings": {"properties": {
                    "incident_id": {"type": "keyword"},
                    "decision": {"type": "keyword"},
                    "risk_score": {"type": "float"},
                    "service": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "ville": {"type": "keyword"},
                    "description": {"type": "text"},
                    "created_at": {"type": "date"},
                    "resolved": {"type": "boolean"},
                    "resolved_at": {"type": "date"},
                }}
            })
        print("✅ Elasticsearch connected and indices ready.")
    except Exception as e:
        print(f"⚠️ Startup error: {e}")

@app.get("/")
def root():
    return {"status": "ok", "project": "AfriGov Sentinel", "version": "2.0.0"}

@app.get("/health")
def health():
    try:
        info = check_connection()
        return {"status": "healthy", "elasticsearch": info["version"]["number"]}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.post("/report-incident")
async def report_incident(report: IncidentReport):
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
    incident = {
        "incident_id": incident_id,
        "description": report.description,
        "service": report.service,
        "category": report.category,
        "severity": report.severity,
        "status": "En cours",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ville": report.ville,
        "region": report.region,
        "reporter_type": report.reporter_type,
        "priority": _compute_priority(report.severity),
        "sla_hours": _compute_sla(report.severity),
        "assigned_to": f"Responsable {report.service}",
    }
    if report.lat and report.lon:
        incident["location"] = {"lat": report.lat, "lon": report.lon}

    try:
        es_id = index_incident(incident)
        incident["_es_id"] = es_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ES error: {e}")

    try:
        similar = get_similar_incidents(report.description, report.category, report.ville)
    except Exception:
        similar = []

    analysis = await analyze_incident(incident, similar)

    decision_doc = {
        "incident_id": incident_id,
        "risk_score": analysis["risk_score"],
        "decision": analysis["decision"],
        "explanation": analysis["explanation"],
        "action_plan": analysis["action_plan"],
        "contact": analysis.get("contact", {}),
        "similar_incidents_count": len(similar),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        log_decision(decision_doc)
    except Exception as e:
        print(f"⚠️ Could not log decision: {e}")

    # Auto-escalate critical incidents
    if analysis["decision"] == "CRITICAL_ESCALATION":
        try:
            es.index(index="escalations", document={
                "incident_id": incident_id,
                "decision": analysis["decision"],
                "risk_score": analysis["risk_score"],
                "service": report.service,
                "region": report.region,
                "ville": report.ville,
                "description": report.description,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "resolved": False,
            })
        except Exception as e:
            print(f"⚠️ Could not log escalation: {e}")

    return {
        "incident_id": incident_id,
        "status": "Analysé",
        "analysis": {
            "risk_score": analysis["risk_score"],
            "decision": analysis["decision"],
            "decision_label": _decision_label(analysis["decision"]),
            "explanation": analysis["explanation"],
            "action_plan": analysis["action_plan"],
            "contact": analysis.get("contact", {}),
            "similar_incidents_found": len(similar),
            "context": analysis.get("context", {}),
        },
    }

@app.get("/incidents")
def list_incidents(size: int = 100):
    try:
        incidents = get_all_incidents(size=size)
        return {"total": len(incidents), "incidents": incidents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def stats():
    try:
        return get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/escalations")
def get_escalations():
    try:
        resp = es.search(index="escalations", body={
            "query": {"term": {"resolved": False}},
            "sort": [{"created_at": {"order": "desc"}}],
            "size": 50,
        })
        return {"total": len(resp["hits"]["hits"]), "escalations": [h["_source"] for h in resp["hits"]["hits"]]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/incidents/{incident_id}/status")
def update_status(incident_id: str, update: StatusUpdate):
    try:
        resp = es.search(index=INDEX_INCIDENTS, body={"query": {"term": {"incident_id": incident_id}}})
        hits = resp["hits"]["hits"]
        if not hits:
            raise HTTPException(status_code=404, detail="Incident not found")
        doc_id = hits[0]["_id"]
        es.update(index=INDEX_INCIDENTS, id=doc_id, body={"doc": {"status": update.status}})
        if update.status == "Résolu":
            esc = es.search(index="escalations", body={"query": {"term": {"incident_id": incident_id}}})
            for h in esc["hits"]["hits"]:
                es.update(index="escalations", id=h["_id"], body={"doc": {"resolved": True, "resolved_at": datetime.now(timezone.utc).isoformat()}})
        return {"success": True, "incident_id": incident_id, "new_status": update.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/summary")
def dashboard_summary():
    try:
        stats_data = get_stats()
        # Unresolved critical incidents
        critical = es.search(index=INDEX_INCIDENTS, body={
            "query": {"bool": {"must": [{"term": {"severity": 5}}, {"terms": {"status": ["En cours", "Escaladé"]}}]}},
            "size": 0
        })
        # Pending escalations
        esc = es.search(index="escalations", body={"query": {"term": {"resolved": False}}, "size": 0})
        return {
            **stats_data,
            "unresolved_critical": critical["hits"]["total"]["value"],
            "pending_escalations": esc["hits"]["total"]["value"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _compute_priority(severity: int) -> str:
    return {1: "P5", 2: "P4", 3: "P3", 4: "P2", 5: "P1"}.get(severity, "P5")

def _compute_sla(severity: int) -> int:
    return {1: 72, 2: 48, 3: 24, 4: 8, 5: 2}.get(severity, 72)

def _decision_label(decision: str) -> str:
    return {
        "CRITICAL_ESCALATION": "🔴 Escalade critique — Intervention immédiate",
        "URGENT_ACTION": "🟠 Action urgente — Dans les 24h",
        "STANDARD_PROCESSING": "🟡 Traitement standard",
        "MONITOR": "🟢 Surveillance passive",
    }.get(decision, decision)