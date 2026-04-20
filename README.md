# 🏃‍♂️🧠 Health Data Coach

**Health Data Coach** est un projet de coach sportif intelligent basé sur les données **Apple Health**, combinant une application iOS et un backend Python pour analyser l’entraînement, dialoguer en langage naturel et formuler des recommandations personnalisées.

---

## 🎯 Objectif du projet

L’objectif n’est **pas** de prédire une performance ou une blessure, mais de :

* aider l’utilisateur à **comprendre ses habitudes d’entraînement**,
* fournir des **bilans clairs et contextualisés** (semaine, mois, année),
* proposer des **recommandations cohérentes et prudentes**,
* agir comme un **coach humain augmenté par les données**.

Le système est conçu pour être **explicable**, **progressif** et **robuste**, même avec des données personnelles limitées.

---

## 🧩 Architecture globale

Le projet repose sur deux briques principales :

```
Health Data Coach
│
├── HealthRunTracker/              # iOS application (SwiftUI)
│   ├── HealthKit data access
│   ├── Local data aggregation
│   ├── Snapshot and CSV generation
│   ├── Chat interface and visualizations
│   └── Weekly, monthly, and yearly summaries
│
├── HealthCoachBackend/            # Python backend
│   ├── FastAPI REST API
│   ├── Intent detection and routing
│   ├── Snapshot-based data analysis
│   ├── Recommendation and coaching engine
│   ├── Agent-based logic
│   └── LLM integration (via Ollama)
│
└── models/                        # Trained machine learning models
    └── Serialized models (joblib)
```

---

## 📱 HealthRunTracker (iOS)

**Technologies** : SwiftUI, HealthKit

Documentation dédiée : [`HealthRunTracker/README.md`](HealthRunTracker/README.md)

### Rôle

* Accès sécurisé aux données Apple Health
* Extraction des séances de course
* Agrégation hebdomadaire
* Envoi des données vers le backend
* Interface de chat avec le coach

### Données collectées

Par séance :

* distance
* durée
* allure
* zones d’intensité (Z1–Z5)

Par semaine :

* volume total
* nombre de séances
* durée cumulée
* charge hebdomadaire

---

## 🧠 HealthCoachBackend (Python)

**Technologies** : FastAPI, Pandas, scikit-learn, LLM (via Ollama)

### Modules principaux

* **API REST** (FastAPI)
* **Analyse temporelle** (semaine / mois / année)
* **Chatbot NLP** avec routage strict
* **Moteur de recommandation hybride**
* **Gestion de mémoire conversationnelle**

---

## 🤖 Chatbot NLP

Le chatbot est piloté par un **moteur de décision strict** qui distingue :

* small talk
* questions factuelles
* comparaisons temporelles
* bilans
* coaching long terme
* recommandations

👉 Le LLM ne décide jamais de la période ou du type de réponse : il **verbalise uniquement** des décisions structurées produites par le backend.

### Exemples de requêtes gérées

* "Combien de km cette semaine ?"
* "Compare ce mois avec le mois dernier"
* "Fais-moi un bilan"
* "Suis-je régulier ?"
* "Fais-moi une recommandation"

---

## 📊 Moteur de recommandation

Le moteur repose sur un pipeline **hybride et explicable** :

### 1. Clustering des séances (micro)

* KMeans (3 clusters)
* Séances : easy / endurance / intensity

### 2. Clustering des semaines (macro)

* KMeans (3 clusters)
* Profils de charge hebdomadaire

### 3. Apprentissage de la structure des semaines

* Distribution moyenne des types de séances par cluster de semaine
* Génération de templates data-driven

### 4. Score de risque (ML)

* Régression logistique
* Sortie probabiliste `risk_proba ∈ [0,1]`
* Indicateur de vigilance (pas médical)

### 5. Modulation par le risque

* Réduction de l’intensité si risque élevé
* Possibilité d’intensité si risque faible

### 6. Ajustement temps réel

* Retrait des séances déjà effectuées
* Si semaine complète → planification semaine suivante

---

## 📦 Sortie du moteur

Le backend produit un objet structuré, par exemple :

```json
{
  "target_sessions": 3,
  "dominant_week_cluster": 1,
  "avg_risk_last_3w": 0.61,
  "risk_level": "moderate",
  "base_plan": ["intensity", "easy", "endurance"],
  "remaining_sessions": ["easy", "endurance"],
  "week_complete": false
}
```

Cet objet est ensuite **verbalisé par le LLM**, sans modification de la logique.

---

## 🧪 Philosophie du projet

* ✅ Pas de boîte noire
* ✅ Pas de sur-optimisation
* ✅ Décisions explicables
* ✅ Séparation stricte logique / langage
* ✅ Approche coach > prédicteur

Le système **corrige les habitudes** plutôt que de les reproduire aveuglément.

---

## 🚧 Fonctionnalités en cours / à venir
Several extensions could significantly enhance the current system, both in terms of intelligence and user experience.

### 1. Integration of an External LLM (e.g. Mistral AI)
One possible improvement would be to integrate an external Large Language Model such as Mistral AI, which offers a free-tier API.
Objectives:
- Improve the natural language quality of explanations and recommendations.
- Generate more contextual, human-like coaching feedback.
- Keep the core logic deterministic (risk computation, clustering, constraints) while delegating only the verbalization and reasoning to the LLM.

Technical approach:

- The backend would keep full control of:
    - Training data
    - Risk indicators
    - Weekly statistics
    - Business rules

- The LLM would only receive:
    - Structured inputs (JSON)
    - Strict prompts describing what it is allowed and forbidden to do

This separation ensures reliability, reproducibility, and avoids uncontrolled model behavior.

### 2. Personalized Training Plan for Race Preparation
Another major extension would be to build a long-term training plan generator designed to prepare a runner for a specific race (e.g. 10 km, half-marathon, marathon).

User input questionnaire:
- To generate such a plan, the user would be asked to provide:
- Target race and race date
- Current VMA (or estimated VMA)
- Previous personal records (5 km, 10 km, half-marathon, etc.)
- Training objective (finish, improve time, performance target)
- Usual number of weekly sessions
- Maximum acceptable number of sessions
- Preferred training days (optional)

Plan generation logic:
- The model would generate a progressive multi-week plan
- Weekly volume would be based on:
- The runner’s historical average distance
- The runner’s current training frequency
- Intensity distribution would follow safe progression rules
- Key sessions (long run, intensity, recovery) would be scheduled consistently

Built-in safety alerts:
- The system would automatically detect unrealistic or risky configurations, for example:
- Requesting 5 sessions per week while the historical average is 3
- A sudden increase in weekly distance beyond safe thresholds
- Excessive intensity accumulation over consecutive weeks

In such cases, the system would:
- Warn the user
- Propose a safer alternative
- Explain the risk clearly

### 3. Progressive Load and Distance Monitoring
An additional improvement would be to introduce forward-looking load monitoring.

Features:
- Track expected weekly distance for upcoming weeks
- Compare projected load with the runner’s historical baseline
- Visualize gradual progression (or detect abrupt changes)
- Adjust recommendations dynamically based on real completed sessions

This would allow:
- Better anticipation of overtraining risk
- Smarter long-term progression
- More adaptive training plans

### 4. Persistent Data Storage with a Lightweight Database
Currently, data is processed from CSV files, which is sufficient for prototyping but not optimal for scaling.

Proposed improvement:
- Introduce a lightweight, free-tier database (e.g. SQLite, PostgreSQL free tier, or cloud-based free services)

Benefits:
- Faster access to historical data
- Easier session and week aggregation
- Persistent user profiles and training history
- Better performance for repeated queries and recommendations

This would also enable:
- Multi-user support
- Long-term tracking
- More advanced analytics without recomputing everything from scratch
