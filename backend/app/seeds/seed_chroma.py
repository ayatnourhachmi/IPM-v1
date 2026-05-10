"""Seed ChromaDB with 20 synthetic business needs for demo and duplicate detection."""

from __future__ import annotations

import logging

from app.core.chroma import get_collection
from app.core.embedding_client import embed_texts

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 20 realistic synthetic business needs (French, DXC innovation context)
# ---------------------------------------------------------------------------

SEED_NEEDS: list[dict[str, str | list[str] | dict]] = [
    {
        "id": "BN-2025-001",
        "pitch": "Mettre en place un chatbot intelligent basé sur l'IA générative pour le support client interne, capable de répondre aux questions fréquentes sur les processus RH et IT en temps réel.",
        "horizon": "court_terme",
        "status": "submitted",
        "tags": {"objectif": "cx_improvement", "domaine": ["IA", "RH"], "impact": ["Cost", "CustomerExperience"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-002",
        "pitch": "Développer une plateforme de détection des anomalies sur les flux financiers en utilisant des modèles de machine learning pour identifier les transactions suspectes avant validation.",
        "horizon": "moyen_terme",
        "status": "in_qualification",
        "tags": {"objectif": "risk_mitigation", "domaine": ["IA", "Finance"], "impact": ["Risk", "Cost"], "origine": "enjeu_marche"},
    },
    {
        "id": "BN-2025-003",
        "pitch": "Migrer l'infrastructure on-premise vers une architecture cloud hybride multi-tenant pour réduire les coûts d'hébergement de 40% tout en améliorant la résilience.",
        "horizon": "long_terme",
        "status": "draft",
        "tags": {"objectif": "cost_reduction", "domaine": ["Cloud", "Operations"], "impact": ["Cost", "Risk"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-004",
        "pitch": "Implémenter une solution zero-trust pour sécuriser les accès distants des collaborateurs en télétravail avec authentification biométrique et analyse comportementale.",
        "horizon": "moyen_terme",
        "status": "submitted",
        "tags": {"objectif": "risk_mitigation", "domaine": ["Cybersecurite"], "impact": ["Risk"], "origine": "enjeu_marche"},
    },
    {
        "id": "BN-2025-005",
        "pitch": "Créer un data lake unifié consolidant toutes les sources de données clients pour permettre des analyses prédictives cross-canal et améliorer le taux de rétention.",
        "horizon": "long_terme",
        "status": "rework",
        "tags": {"objectif": "cx_improvement", "domaine": ["Data", "Cloud"], "impact": ["Revenue", "CustomerExperience"], "origine": "demande_client"},
    },
    {
        "id": "BN-2025-006",
        "pitch": "Automatiser le processus de recrutement avec un outil d'évaluation des CV par intelligence artificielle, incluant le screening initial et le scoring des candidatures.",
        "horizon": "court_terme",
        "status": "draft",
        "tags": {"objectif": "cost_reduction", "domaine": ["IA", "RH"], "impact": ["Cost"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-007",
        "pitch": "Lancer une application mobile de self-service pour les clients entreprise permettant le suivi en temps réel des tickets, la consultation des SLA et la communication directe avec l'équipe support.",
        "horizon": "moyen_terme",
        "status": "in_qualification",
        "tags": {"objectif": "cx_improvement", "domaine": ["Operations"], "impact": ["CustomerExperience", "Revenue"], "origine": "demande_client"},
    },
    {
        "id": "BN-2025-008",
        "pitch": "Déployer une solution RPA (Robotic Process Automation) pour automatiser les rapprochements comptables mensuels et éliminer les erreurs manuelles dans la consolidation financière.",
        "horizon": "court_terme",
        "status": "submitted",
        "tags": {"objectif": "cost_reduction", "domaine": ["Finance", "IA"], "impact": ["Cost", "Risk"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-009",
        "pitch": "Concevoir un programme de formation en ligne gamifié sur la cybersécurité pour sensibiliser les 5000 collaborateurs aux risques de phishing et d'ingénierie sociale.",
        "horizon": "court_terme",
        "status": "abandoned",
        "tags": {"objectif": "risk_mitigation", "domaine": ["Cybersecurite", "RH"], "impact": ["Risk"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-010",
        "pitch": "Mettre en place un système de monitoring prédictif de l'infrastructure IT utilisant l'analyse de séries temporelles pour anticiper les pannes 24h à l'avance.",
        "horizon": "moyen_terme",
        "status": "draft",
        "tags": {"objectif": "cost_reduction", "domaine": ["IA", "Operations"], "impact": ["Cost", "Risk"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-011",
        "pitch": "Explorer les opportunités de blockchain pour la traçabilité des contrats et la gestion décentralisée des documents juridiques entre partenaires commerciaux.",
        "horizon": "long_terme",
        "status": "abandoned",
        "tags": {"objectif": "market_opportunity", "domaine": ["Autre", "Operations"], "impact": ["Risk", "Revenue"], "origine": "enjeu_marche"},
    },
    {
        "id": "BN-2025-012",
        "pitch": "Optimiser la supply chain logistique avec un jumeau numérique permettant de simuler différents scénarios de distribution et réduire les délais de livraison de 25%.",
        "horizon": "long_terme",
        "status": "submitted",
        "tags": {"objectif": "cost_reduction", "domaine": ["IA", "Operations"], "impact": ["Cost", "CustomerExperience"], "origine": "enjeu_marche"},
    },
    {
        "id": "BN-2025-013",
        "pitch": "Développer un portail client unifié avec personnalisation IA des recommandations de services, intégrant un moteur de suggestion basé sur l'historique d'utilisation.",
        "horizon": "moyen_terme",
        "status": "draft",
        "tags": {"objectif": "cx_improvement", "domaine": ["IA", "Data"], "impact": ["Revenue", "CustomerExperience"], "origine": "demande_client"},
    },
    {
        "id": "BN-2025-014",
        "pitch": "Mettre en conformité RGPD l'ensemble des traitements de données personnelles avec un outil automatisé de cartographie des flux et de gestion du consentement.",
        "horizon": "court_terme",
        "status": "in_qualification",
        "tags": {"objectif": "risk_mitigation", "domaine": ["Data", "Cybersecurite"], "impact": ["Risk"], "origine": "enjeu_marche"},
    },
    {
        "id": "BN-2025-015",
        "pitch": "Créer une marketplace interne de microservices et d'APIs réutilisables pour accélérer le développement de nouvelles applications et réduire la duplication de code.",
        "horizon": "moyen_terme",
        "status": "rework",
        "tags": {"objectif": "cost_reduction", "domaine": ["Cloud", "Operations"], "impact": ["Cost"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-016",
        "pitch": "Proposer un service de business intelligence en temps réel avec des dashboards interactifs alimentés par des données consolidées multi-sources pour les directions métier.",
        "horizon": "court_terme",
        "status": "submitted",
        "tags": {"objectif": "market_opportunity", "domaine": ["Data", "IA"], "impact": ["Revenue"], "origine": "demande_client"},
    },
    {
        "id": "BN-2025-017",
        "pitch": "Déployer une infrastructure de edge computing pour réduire la latence des applications IoT industrielles et permettre le traitement des données au plus près des capteurs.",
        "horizon": "long_terme",
        "status": "draft",
        "tags": {"objectif": "market_opportunity", "domaine": ["Cloud", "Operations"], "impact": ["Revenue", "Cost"], "origine": "enjeu_marche"},
    },
    {
        "id": "BN-2025-018",
        "pitch": "Automatiser la génération de rapports réglementaires pour le département conformité en utilisant le NLP pour extraire et structurer les informations pertinentes des documents internes.",
        "horizon": "court_terme",
        "status": "in_qualification",
        "tags": {"objectif": "cost_reduction", "domaine": ["IA", "Finance"], "impact": ["Cost", "Risk"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-019",
        "pitch": "Implémenter un programme de bien-être digital pour les collaborateurs avec une application de suivi de charge de travail, détection de surcharge et recommandations personnalisées.",
        "horizon": "moyen_terme",
        "status": "abandoned",
        "tags": {"objectif": "cx_improvement", "domaine": ["RH", "IA"], "impact": ["CustomerExperience"], "origine": "probleme_operationnel"},
    },
    {
        "id": "BN-2025-020",
        "pitch": "Construire une plateforme d'innovation ouverte connectant les startups technologiques avec les besoins métier internes pour co-développer des solutions via des POC rapides.",
        "horizon": "long_terme",
        "status": "draft",
        "tags": {"objectif": "market_opportunity", "domaine": ["Autre", "IA"], "impact": ["Revenue", "CustomerExperience"], "origine": "enjeu_marche"},
    },
]


def seed_chromadb() -> None:
    """Insert 20 synthetic business needs into ChromaDB if the collection is empty."""
    collection = get_collection()

    if collection.count() > 0:
        logger.info("ChromaDB collection already seeded (%d entries), skipping.", collection.count())
        return

    logger.info("Seeding ChromaDB with %d synthetic business needs...", len(SEED_NEEDS))

    pitches = [need["pitch"] for need in SEED_NEEDS]
    ids = [need["id"] for need in SEED_NEEDS]
    metadatas = [{"status": need["status"]} for need in SEED_NEEDS]

    # Batch embed all pitches
    embeddings = embed_texts(pitches)  # type: ignore[arg-type]

    collection.add(
        ids=ids,  # type: ignore[arg-type]
        embeddings=embeddings,
        documents=pitches,  # type: ignore[arg-type]
        metadatas=metadatas,  # type: ignore[arg-type]
    )

    logger.info("ChromaDB seeded successfully with %d entries.", len(SEED_NEEDS))
