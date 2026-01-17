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
├── HealthRunTracker/        # App iOS (SwiftUI)
│   ├── HealthKit access
│   ├── Data export (CSV)
│   └── Chat UI, graphs
│
├── HealthCoachBackend/      # Backend Python
│   ├── FastAPI
│   ├── NLP / LLM routing
│   ├── Recommendation engine
│   └── ML models
│
└── models/                  # Modèles ML entraînés (joblib)
```

---

## 📱 HealthRunTracker (iOS)

**Technologies** : SwiftUI, HealthKit

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

* Recommandations multi-semaines


