import os
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

ELASTIC_URL = os.getenv("ELASTIC_URL")
ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")

INDEX_INCIDENTS = "incidents"
INDEX_DECISIONS = "agent_decisions"

es = Elasticsearch(
    ELASTIC_URL,
    api_key=ELASTIC_API_KEY,
    verify_certs=True,
)


def check_connection():
    return es.info()


def create_indices():
    """Create indices if they don't exist."""

    incidents_mapping = {
        "mappings": {
            "properties": {
                "incident_id": {"type": "keyword"},
                "description": {"type": "text"},
                "service": {"type": "keyword"},
                "category": {"type": "keyword"},
                "severity": {"type": "integer"},
                "status": {"type": "keyword"},
                "created_at": {"type": "date"},
                "ville": {"type": "keyword"},
                "region": {"type": "keyword"},
                "location": {"type": "geo_point"},
                "reporter_type": {"type": "keyword"},
                "priority": {"type": "keyword"},
                "sla_hours": {"type": "integer"},
                "assigned_to": {"type": "keyword"},
            }
        }
    }

    decisions_mapping = {
        "mappings": {
            "properties": {
                "incident_id": {"type": "keyword"},
                "risk_score": {"type": "float"},
                "decision": {"type": "keyword"},
                "explanation": {"type": "text"},
                "action_plan": {"type": "text"},
                "similar_incidents_count": {"type": "integer"},
                "created_at": {"type": "date"},
            }
        }
    }

    if not es.indices.exists(index=INDEX_INCIDENTS):
        es.indices.create(index=INDEX_INCIDENTS, body=incidents_mapping)
        print(f"Index '{INDEX_INCIDENTS}' created.")

    if not es.indices.exists(index=INDEX_DECISIONS):
        es.indices.create(index=INDEX_DECISIONS, body=decisions_mapping)
        print(f"Index '{INDEX_DECISIONS}' created.")


def index_incident(incident: dict) -> str:
    """Index an incident into Elasticsearch."""
    resp = es.index(index=INDEX_INCIDENTS, document=incident)
    return resp["_id"]


def get_similar_incidents(description: str, category: str, ville: str, size: int = 5) -> list:
    """Search for similar incidents using full-text + filters."""
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"description": description}}
                ],
                "should": [
                    {"term": {"category": category}},
                    {"term": {"ville": ville}},
                ],
                "boost": 1.5,
            }
        },
        "size": size,
    }
    resp = es.search(index=INDEX_INCIDENTS, body=query)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def get_recent_incidents_by_service(service: str, size: int = 10) -> list:
    """Get recent incidents for a given service."""
    query = {
        "query": {"term": {"service": service}},
        "sort": [{"created_at": {"order": "desc"}}],
        "size": size,
    }
    resp = es.search(index=INDEX_INCIDENTS, body=query)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def log_decision(decision: dict) -> str:
    """Log agent decision into Elasticsearch."""
    resp = es.index(index=INDEX_DECISIONS, document=decision)
    return resp["_id"]


def get_all_incidents(size: int = 100) -> list:
    """Get all incidents ordered by date."""
    query = {
        "query": {"match_all": {}},
        "sort": [{"created_at": {"order": "desc"}}],
        "size": size,
    }
    resp = es.search(index=INDEX_INCIDENTS, body=query)
    return [hit["_source"] for hit in resp["hits"]["hits"]]


def get_stats() -> dict:
    """Get basic stats using ES aggregations."""
    query = {
        "size": 0,
        "aggs": {
            "by_category": {
                "terms": {"field": "category", "size": 10}
            },
            "by_severity": {
                "terms": {"field": "severity", "size": 5}
            },
            "by_region": {
                "terms": {"field": "region", "size": 10}
            },
            "avg_severity": {
                "avg": {"field": "severity"}
            },
        },
    }
    resp = es.search(index=INDEX_INCIDENTS, body=query)
    aggs = resp["aggregations"]
    return {
        "total_incidents": resp["hits"]["total"]["value"],
        "by_category": {b["key"]: b["doc_count"] for b in aggs["by_category"]["buckets"]},
        "by_severity": {b["key"]: b["doc_count"] for b in aggs["by_severity"]["buckets"]},
        "by_region": {b["key"]: b["doc_count"] for b in aggs["by_region"]["buckets"]},
        "avg_severity": round(aggs["avg_severity"]["value"] or 0, 2),
    }