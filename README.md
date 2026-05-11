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
├── scripts/
│   └── dev_phone.sh                   # Lance backend + build + installation iPhone
│
├── render.yaml                        # Blueprint Render pour heberger l'API FastAPI
│
└── README.md                          # Vue globale du projet
```

Documentation spécifique à l'app iOS : [HealthRunTracker/README.md](HealthRunTracker/README.md)

Documentation spécifique au backend Python : [HealthCoachBackend/README.md](HealthCoachBackend/README.md)

## Flux principal

1. L'utilisateur ouvre l'app iOS sur son iPhone.
2. L'app demande l'accès HealthKit si nécessaire.
3. Les données semaine/année sont chargées localement.
4. L'app demande au backend la dernière séance connue, puis synchronise seulement les nouveautés.
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
- détail d'une séance avec catégorie affichée ou prédite
- saisie utilisateur de la catégorie et du détail de séance
- fusion optionnelle de deux séances du même jour quand il s'agit d'un arrêt/reprise accidentel
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
- `GET /api/run-sessions/metadata` : métadonnées de séance, catégorie persistée, prédiction et détails
- `PATCH /api/run-sessions/metadata` : mise à jour utilisateur de `session_type` et `session_detail`
- `POST /api/run-sessions/merge` : fusion de deux séances proches dans le temps
- routes de chat, imports, séances et signatures dans `HealthCoachBackend/api/`

Au démarrage, le backend reconstruit certaines agrégations si nécessaire et lance aussi les tâches d'import CSV existantes.

## Lancer l'environnement iPhone

Depuis la racine du projet, la commande la plus simple est :

```bash
./scripts/dev_phone.sh
```

Ou via `make` :

```bash
make phone
```

Elle automatise le flux de développement local :

- redémarre le backend sur `0.0.0.0:8000`
- vérifie `http://MacBook-Pro-de-Albane.local:8000/health/db`
- build l'app iOS en Debug
- installe l'app sur l'iPhone connecté
- lance l'app

Le script utilise `/tmp/HealthCoachDerivedData` pour éviter les erreurs de signature liées aux dossiers iCloud.

## Lancer le backend seul

Depuis la racine du projet :

```bash
cd HealthCoachBackend
venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Raccourcis utiles depuis la racine :

```bash
make backend
make backend-log
make backend-stop
make streamlit
make streamlit-8502
```

L'app iOS choisit maintenant son URL selon l'environnement :

```text
HealthRunTracker/HealthRunTracker/App/APIConfig.swift
```

Configuration actuelle :

```swift
enum APIConfig {
    // Debug: http://MacBook-Pro-de-Albane.local:8000
    // Release: https://healthcoach-api-ri82.onrender.com
}
```

Cela evite de modifier l'app quand on passe du backend local a l'API hebergee. Les valeurs peuvent aussi etre surchargees avec les build settings `HEALTHCOACH_API_BASE_URL` et `HEALTHCOACH_IMPORT_TOKEN`.

## Déploiement Render

Le fichier `render.yaml` declare le backend comme service web Python gratuit sur Render, avec `HealthCoachBackend` comme dossier racine.

Variables a renseigner dans Render :

```env
DATABASE_URL=
DEFAULT_USER_ID=
IMPORT_API_TOKEN=
```

`IMPORT_API_TOKEN` protege les routes d'ingestion `POST /api/run-session` et `POST /api/run-sessions/batch`. L'app iOS doit etre build avec le meme token via `HEALTHCOACH_IMPORT_TOKEN`.

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

La synchronisation est déclenchée automatiquement au lancement de l'app et quand l'app redevient active.

Côté iOS :

- `HealthManager.startAutomaticSyncOnLaunch()` démarre le flux
- `RunSessionSyncService.fetchLatestSessionStartTime(...)` lit la dernière séance stockée
- `HealthManager.syncLatestRunSessions()` collecte seulement les séances récentes, avec une marge de deux jours
- `HealthManager.prepareSessionsForExport(_:)` filtre les séances invalides
- `RunSessionSyncService.uploadBatch(...)` envoie les lots au backend

Côté backend :

- `GET /api/run-sessions/latest` retourne la dernière séance connue
- `POST /api/run-sessions/batch` reçoit les séances
- la base Neon est utilisée comme source persistante
- les signatures sont invalidées seulement lorsque les données changent réellement

Une synchronisation réussie se voit dans les logs backend avec :

```text
POST /api/run-sessions/batch HTTP/1.1 200 OK
```

## Métadonnées de séance

Chaque séance peut maintenant porter deux champs métier :

- `session_type` : catégorie validée par l'utilisateur (`footing`, `fractionné`, `sortie longue`, etc.)
- `session_detail` : détail libre de la séance, par exemple `6x400 R100 4:20/km`

Comportement actuel :

- si `session_type` existe déjà en base, l'écran détail affiche la séance en lecture seule
- si `session_type` est vide, le backend renvoie une `predicted_session_type`
- l'utilisateur peut confirmer ou corriger la catégorie puis saisir `session_detail`
- la validation persiste les données en base via `PATCH /api/run-sessions/metadata`

La prédiction actuelle côté backend est volontairement simple :

- entraînement à la volée d'une `LogisticRegression` sur les séances déjà labellisées du même utilisateur
- fallback heuristique si le volume de labels est insuffisant

Cette prédiction sert d'aide à la saisie. Le label de vérité reste celui validé par l'utilisateur.

## Fusion de séances

La vue semaine permet de sélectionner un jour contenant plusieurs séances.
Si le jour contient exactement deux séances, l'app propose une fusion explicite.

Cas d'usage :

- arrêt/reprise accidentel d'une même sortie
- découpage HealthKit parasite alors qu'il n'y a qu'une seule vraie séance

Principe de fusion :

- une séance `anchor` est conservée
- la seconde séance est absorbée dans l'anchor
- l'app n'affiche ensuite plus qu'une seule séance logique

Important :

- la fusion doit rester optionnelle, car deux séances le même jour peuvent être normales
- la fusion n'est pas destinée à remplacer une modélisation plus avancée des "vraies séances"

## Migrations SQL requises

Certaines fonctionnalités récentes nécessitent des migrations manuelles dans Neon.

Colonnes `session_type` et `session_detail` :

```sql
ALTER TABLE run_sessions
ADD COLUMN IF NOT EXISTS session_type TEXT;

ALTER TABLE run_sessions
ADD COLUMN IF NOT EXISTS session_detail TEXT;
```

Colonne technique de fusion :

```sql
ALTER TABLE run_sessions
ADD COLUMN IF NOT EXISTS merged_into_start_time TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_run_sessions_merged_into_start_time
ON run_sessions (merged_into_start_time);
```

Table d'alias de fusion :

Cette table mémorise qu'une séance HealthKit brute a déjà été absorbée dans une autre, afin d'éviter sa recréation au prochain sync si l'on choisit de ne garder qu'une seule ligne finale dans `run_sessions`.

```sql
CREATE TABLE IF NOT EXISTS run_session_merge_aliases (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  source_start_time TIMESTAMP NOT NULL,
  target_start_time TIMESTAMP NOT NULL,
  CONSTRAINT uq_run_merge_alias_user_source UNIQUE (user_id, source_start_time)
);

CREATE INDEX IF NOT EXISTS idx_run_session_merge_aliases_user_id
ON run_session_merge_aliases (user_id);

CREATE INDEX IF NOT EXISTS idx_run_session_merge_aliases_source_start_time
ON run_session_merge_aliases (source_start_time);

CREATE INDEX IF NOT EXISTS idx_run_session_merge_aliases_target_start_time
ON run_session_merge_aliases (target_start_time);
```

Sans cette table d'alias, une séance supprimée après fusion risque d'être recréée plus tard par le flux de synchronisation HealthKit.

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
3. Verifier que `APIConfig.baseURL` cible le bon environnement.
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
