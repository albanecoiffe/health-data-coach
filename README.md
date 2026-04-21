# Health Data Coach

Health Data Coach est un projet de coach sportif intelligent basé sur les données Apple Health.

Le système combine :

- une app iOS SwiftUI qui lit HealthKit, affiche les données de course et synchronise les séances
- un backend FastAPI qui stocke les données dans Neon, analyse l'entraînement et répond au chat
- des modules de recommandation qui produisent des bilans et conseils prudents, explicables et contextualisés

L'objectif n'est pas de prédire une performance ou une blessure. L'objectif est d'aider l'utilisateur à comprendre ses habitudes d'entraînement, suivre sa progression et recevoir des recommandations cohérentes.

## Architecture

```text
HealthCoach/
├── HealthRunTracker/                  # Application iOS SwiftUI
│   ├── README.md                      # Documentation dédiée à l'app
│   └── HealthRunTracker/
│       ├── App/                       # Entrée app, navigation, configuration API
│       ├── Features/                  # Vues semaine, année, carte, chat
│       ├── HealthKit/                 # Autorisations, lecture et agrégations Apple Health
│       ├── Sync/                      # Export des séances vers le backend
│       ├── Models/                    # Modèles Swift
│       ├── Core/
│       ├── Utils/
│       └── Debug/
│
├── HealthCoachBackend/                # Backend Python FastAPI
│   ├── api/                           # Routes REST
│   ├── core/                          # Services, modèles SQLAlchemy, logique métier
│   ├── execution/                     # Exécution des intentions détectées
│   ├── intents/                       # Détection d'intention
│   ├── normalization/                 # Résolution dates/périodes
│   ├── recommendation/                # Recommandations et risque d'entraînement
│   ├── routing/                       # Routage des requêtes
│   ├── schemas/                       # Schémas API
│   ├── verbalization/                 # Mise en langage des réponses
│   ├── database.py                    # Connexion Neon/PostgreSQL
│   └── main.py                        # Entrée FastAPI
│
└── README.md                          # Vue globale du projet
```

Documentation spécifique à l'app iOS : [HealthRunTracker/README.md](HealthRunTracker/README.md)

Documentation spécifique au backend Python : [HealthCoachBackend/README.md](HealthCoachBackend/README.md)

## Flux principal

1. L'utilisateur ouvre l'app iOS sur son iPhone.
2. L'app demande l'accès HealthKit si nécessaire.
3. Les données semaine/année sont chargées localement.
4. Les séances des 24 derniers mois sont synchronisées automatiquement vers le backend.
5. Le backend stocke ou met à jour les séances dans Neon.
6. Le chat interroge le backend pour produire des bilans, comparaisons, métriques et recommandations.

La page de synchronisation manuelle côté app a été retirée : l'app s'ouvre directement sur la vue semaine.

## Application iOS

Technologies principales :

- SwiftUI
- HealthKit
- MapKit
- Charts
- URLSession

Fonctions principales :

- lecture des workouts de course Apple Health
- récupération des distances, durées, fréquences cardiaques, calories, dénivelé et traces GPS
- calcul des zones cardiaques Z1 à Z5
- vue semaine avec statistiques, graphe distance et zones cardiaques
- vue année
- vue carte des parcours
- chat avec le coach backend
- synchronisation automatique vers Neon via le backend

Point important : HealthKit doit être testé sur un iPhone physique. Le simulateur ne donne pas accès aux vraies données Apple Health.

## Backend

Technologies principales :

- FastAPI
- SQLAlchemy
- PostgreSQL via Neon
- Pandas
- scikit-learn
- Ollama ou LLM local pour la verbalisation selon la configuration

Routes importantes :

- `GET /` : vérification simple du backend
- `GET /health/db` : vérification de la connexion base de données
- `POST /api/run-sessions/batch` : réception des séances envoyées par l'app iOS
- routes de chat, imports, séances et signatures dans `HealthCoachBackend/api/`

Au démarrage, le backend reconstruit certaines agrégations si nécessaire et lance aussi les tâches d'import CSV existantes.

## Lancer le backend

Depuis la racine du projet :

```bash
cd HealthCoachBackend
venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

L'app iOS doit pointer vers l'adresse IP locale du Mac dans :

```text
HealthRunTracker/HealthRunTracker/App/APIConfig.swift
```

Exemple :

```swift
enum APIConfig {
    static let baseURL = "http://192.168.1.165:8000"
}
```

Si l'adresse IP du Mac change, cette valeur doit être mise à jour avant de relancer l'app sur l'iPhone.

## Lancer l'app iOS

Depuis Xcode :

1. ouvrir `HealthRunTracker/HealthRunTracker.xcodeproj`
2. sélectionner le scheme `HealthRunTracker`
3. sélectionner l'iPhone physique
4. lancer l'app

Build en ligne de commande :

```bash
xcodebuild \
  -project HealthRunTracker/HealthRunTracker.xcodeproj \
  -scheme HealthRunTracker \
  -configuration Debug \
  -destination 'platform=iOS,id=00008120-00146C502210201E' \
  build
```

L'identifiant `00008120-00146C502210201E` correspond à l'iPhone utilisé actuellement. Il peut changer selon l'appareil.

## Synchronisation Neon

La synchronisation est déclenchée automatiquement au lancement de l'app.

Côté iOS :

- `HealthManager.startAutomaticSyncOnLaunch()` démarre le flux
- `HealthManager.syncRecentRunSessionsOnLaunch()` collecte les 24 derniers mois
- `HealthManager.prepareSessionsForExport(_:)` filtre les séances invalides
- `RunSessionSyncService.uploadBatch(...)` envoie les lots au backend

Côté backend :

- `POST /api/run-sessions/batch` reçoit les séances
- la base Neon est utilisée comme source persistante
- les signatures sont invalidées lorsque les données changent

Une synchronisation réussie se voit dans les logs backend avec :

```text
POST /api/run-sessions/batch HTTP/1.1 200 OK
```

## Qualité des données exportées

Avant envoi, l'app ignore les séances incohérentes :

- date future au-delà d'une petite tolérance
- distance ou durée nulle
- valeurs infinies ou non numériques
- distance supérieure à 200 km
- durée supérieure à 24 h
- fréquence cardiaque moyenne hors plage plausible
- dénivelé ou calories incohérents

Cette étape protège la base Neon contre les exports corrompus ou incomplets.

## Chat et recommandations

Le backend garde la logique métier structurée :

- détection d'intention
- résolution de période
- extraction des métriques
- comparaison entre périodes
- bilan d'entraînement
- recommandation prudente
- verbalisation finale

Le LLM ne doit pas décider seul des métriques ou de la période. Il transforme une décision structurée en réponse lisible.

Exemples de requêtes :

- "Combien de km cette semaine ?"
- "Compare ce mois avec le mois dernier"
- "Fais-moi un bilan"
- "Suis-je régulier ?"
- "Fais-moi une recommandation"

## Vérification rapide

1. Lancer le backend.
2. Vérifier `GET /health/db`.
3. Mettre à jour `APIConfig.baseURL` si besoin.
4. Compiler et lancer l'app sur l'iPhone.
5. Accepter HealthKit.
6. Vérifier que l'app s'ouvre sur la vue semaine.
7. Vérifier dans les logs backend que `/api/run-sessions/batch` retourne `200 OK`.
8. Tester le graphe de zones cardiaques dans la vue semaine.
9. Tester une question dans le chat.

## Principes du projet

- logique explicable plutôt que boîte noire
- séparation entre données, décisions et verbalisation
- prudence dans les recommandations sportives
- priorité aux données réelles Apple Health
- synchronisation automatique mais filtrée avant export
- backend comme source persistante via Neon
