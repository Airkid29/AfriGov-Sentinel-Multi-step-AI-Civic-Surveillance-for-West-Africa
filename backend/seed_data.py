"""
seed_data.py — Populate Elasticsearch with 30 realistic sample incidents.
Run once: python seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from elastic_client import create_indices, index_incident, es, INDEX_INCIDENTS
from datetime import datetime, timedelta, timezone
import random

INCIDENTS = [
    {"description": "Accueil déplorable au bureau des impôts, agents absents depuis 3 jours", "service": "Services Fiscaux", "category": "Qualité médiocre", "severity": 2, "ville": "Aného", "region": "Maritime"},
    {"description": "Panne de courant prolongée à l'hôpital central, générateur en panne", "service": "Santé", "category": "Infrastructure critique", "severity": 5, "ville": "Lomé", "region": "Maritime"},
    {"description": "Distribution irrégulière de l'eau potable dans le quartier Bè depuis 2 semaines", "service": "Eau et Assainissement", "category": "Service interrompu", "severity": 4, "ville": "Lomé", "region": "Maritime"},
    {"description": "Route nationale 1 impraticable après les pluies, plusieurs accidents signalés", "service": "Infrastructures Routières", "category": "Infrastructure critique", "severity": 4, "ville": "Kpalimé", "region": "Plateaux"},
    {"description": "Manque de médicaments essentiels au dispensaire de Tsévié", "service": "Santé", "category": "Pénurie", "severity": 4, "ville": "Tsévié", "region": "Maritime"},
    {"description": "Délai excessif pour obtenir un extrait de naissance, 3 mois d'attente", "service": "État Civil", "category": "Lenteur administrative", "severity": 2, "ville": "Sokodé", "region": "Centrale"},
    {"description": "Corruption signalée à la douane du port de Lomé, demandes de pots-de-vin", "service": "Douanes", "category": "Corruption", "severity": 5, "ville": "Lomé", "region": "Maritime"},
    {"description": "École primaire sans enseignants depuis la rentrée, parents inquiets", "service": "Éducation", "category": "Service interrompu", "severity": 4, "ville": "Atakpamé", "region": "Plateaux"},
    {"description": "Inondations dans le quartier Agbalépédogan, sans réponse des autorités", "service": "Gestion des Catastrophes", "category": "Urgence", "severity": 5, "ville": "Lomé", "region": "Maritime"},
    {"description": "Grève non résolue des agents de collecte des ordures, déchets accumulés", "service": "Assainissement", "category": "Service interrompu", "severity": 3, "ville": "Lomé", "region": "Maritime"},
    {"description": "Pénurie de carburant dans les stations-service de Kara depuis 5 jours", "service": "Énergie", "category": "Pénurie", "severity": 3, "ville": "Kara", "region": "Kara"},
    {"description": "Système informatique de la mairie en panne, impossibilité de traiter les dossiers", "service": "Administration Municipale", "category": "Panne technique", "severity": 3, "ville": "Lomé", "region": "Maritime"},
    {"description": "Agents de police exigent paiement illicite aux barrages routiers", "service": "Sécurité Publique", "category": "Corruption", "severity": 4, "ville": "Kpalimé", "region": "Plateaux"},
    {"description": "Hopital régional sans eau courante depuis une semaine", "service": "Santé", "category": "Infrastructure critique", "severity": 5, "ville": "Dapaong", "region": "Savanes"},
    {"description": "Pont de Gboto endommagé, coupant l'accès à 5 villages", "service": "Infrastructures Routières", "category": "Infrastructure critique", "severity": 5, "ville": "Tabligbo", "region": "Maritime"},
    {"description": "Lycée technique surpeuplé, 80 élèves par classe, conditions inacceptables", "service": "Éducation", "category": "Qualité médiocre", "severity": 3, "ville": "Lomé", "region": "Maritime"},
    {"description": "Pharmacie de l'hôpital régional fermée sans raison depuis 10 jours", "service": "Santé", "category": "Service interrompu", "severity": 4, "ville": "Kara", "region": "Kara"},
    {"description": "Eau contaminée signalée dans plusieurs puits du village", "service": "Eau et Assainissement", "category": "Urgence sanitaire", "severity": 5, "ville": "Notse", "region": "Plateaux"},
    {"description": "Marché central fermé par arrêté sans avertissement préalable", "service": "Commerce", "category": "Décision administrative", "severity": 2, "ville": "Lomé", "region": "Maritime"},
    {"description": "Réseau électrique instable causant des dommages aux équipements électroniques", "service": "Énergie", "category": "Infrastructure critique", "severity": 3, "ville": "Sokodé", "region": "Centrale"},
    {"description": "Personnel médical absent au centre de santé de Bafilo le lundi", "service": "Santé", "category": "Qualité médiocre", "severity": 3, "ville": "Bafilo", "region": "Centrale"},
    {"description": "Déversement de déchets industriels dans la lagune de Lomé", "service": "Environnement", "category": "Urgence environnementale", "severity": 5, "ville": "Lomé", "region": "Maritime"},
    {"description": "Salle d'examen du BACCALAURÉAT sans climatisation, chaleur insupportable", "service": "Éducation", "category": "Conditions inadéquates", "severity": 2, "ville": "Atakpamé", "region": "Plateaux"},
    {"description": "Attente de 6 heures aux urgences de CHU, manque de personnel", "service": "Santé", "category": "Qualité médiocre", "severity": 4, "ville": "Lomé", "region": "Maritime"},
    {"description": "Réseau d'eau vétuste causant des coupures quotidiennes", "service": "Eau et Assainissement", "category": "Infrastructure critique", "severity": 3, "ville": "Aného", "region": "Maritime"},
    {"description": "Fonctionnaire exige paiement pour accélérer un dossier de permis de construire", "service": "Urbanisme", "category": "Corruption", "severity": 4, "ville": "Lomé", "region": "Maritime"},
    {"description": "Bibliothèque universitaire fermée pendant les révisions du semestre", "service": "Éducation", "category": "Service interrompu", "severity": 2, "ville": "Lomé", "region": "Maritime"},
    {"description": "Ambulance du district en panne depuis 3 semaines sans remplacement", "service": "Santé", "category": "Infrastructure critique", "severity": 5, "ville": "Notsé", "region": "Plateaux"},
    {"description": "Absence de signalisation routière dans une zone accidentogène connue", "service": "Infrastructures Routières", "category": "Sécurité publique", "severity": 3, "ville": "Lomé", "region": "Maritime"},
    {"description": "Cimetière municipal sans entretien depuis plusieurs mois", "service": "Administration Municipale", "category": "Qualité médiocre", "severity": 1, "ville": "Tsévié", "region": "Maritime"},
]

LOCS = {
    "Lomé": (6.1375, 1.2123),
    "Aného": (6.2267, 1.5950),
    "Tsévié": (6.4253, 1.2164),
    "Sokodé": (8.9833, 1.1333),
    "Kara": (9.5511, 1.1864),
    "Kpalimé": (6.8978, 0.6406),
    "Atakpamé": (7.5333, 1.1333),
    "Dapaong": (10.8667, 0.2000),
    "Tabligbo": (6.5833, 1.5000),
    "Notse": (6.9500, 1.1667),
    "Bafilo": (9.3500, 1.2500),
    "Notsé": (6.9500, 1.1667),
}

REPORTER_TYPES = ["Citoyen", "ONG", "Journaliste", "Employé municipal", "Médecin"]


def seed():
    print("Creating indices...")
    create_indices()

    # Check if already seeded
    from elasticsearch import NotFoundError
    try:
        count = es.count(index=INDEX_INCIDENTS)["count"]
        if count >= 20:
            print(f"✅ Index already has {count} incidents. Skipping seed.")
            return
    except Exception:
        pass

    print(f"Seeding {len(INCIDENTS)} incidents...")
    now = datetime.now(timezone.utc)

    for i, inc in enumerate(INCIDENTS):
        loc = LOCS.get(inc["ville"], (6.1375, 1.2123))
        jitter_lat = random.uniform(-0.05, 0.05)
        jitter_lon = random.uniform(-0.05, 0.05)

        priority_map = {1: "P5", 2: "P4", 3: "P3", 4: "P2", 5: "P1"}
        sla_map = {1: 72, 2: 48, 3: 24, 4: 8, 5: 2}

        doc = {
            "incident_id": f"INC-{str(i+1).zfill(6)}",
            "description": inc["description"],
            "service": inc["service"],
            "category": inc["category"],
            "severity": inc["severity"],
            "status": random.choice(["En cours", "Résolu", "Escaladé", "En attente"]),
            "created_at": (now - timedelta(days=random.randint(0, 90))).isoformat(),
            "ville": inc["ville"],
            "region": inc["region"],
            "location": {"lat": loc[0] + jitter_lat, "lon": loc[1] + jitter_lon},
            "reporter_type": random.choice(REPORTER_TYPES),
            "priority": priority_map[inc["severity"]],
            "sla_hours": sla_map[inc["severity"]],
            "assigned_to": f"Responsable {inc['service']}",
        }

        es.index(index=INDEX_INCIDENTS, document=doc)
        print(f"  ✅ {doc['incident_id']} — {inc['ville']} — {inc['service']}")

    print(f"\n🎉 Done! {len(INCIDENTS)} incidents indexed.")


if __name__ == "__main__":
    seed()