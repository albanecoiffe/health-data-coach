# HealthCoachBackend

Backend Python du projet Health Data Coach.

Il recoit les seances envoyees par l'app iOS, les stocke dans Neon/PostgreSQL, expose les donnees au chat et calcule les signatures/recommandations d'entrainement.

## Prerequis

- Python avec l'environnement virtuel `venv`
- une base Neon/PostgreSQL accessible
- un fichier local `HealthCoachBackend/.env`
- l'app iOS configuree pour appeler l'IP locale du Mac

Le fichier `.env` contient les vraies valeurs locales et ne doit pas etre pousse dans Git. Le fichier `.env.example` est seulement un modele vide pour documenter les variables attendues.

## Configuration

Variables principales :

```env
DATABASE_URL=
DEFAULT_USER_ID=
USER_ID=
IMPORT_API_TOKEN=
SESSIONS_CSV_PATH=
AUTO_IMPORT_SESSIONS_ON_STARTUP=false
SESSIONS_CSV_POLL_SECONDS=0
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=llama3
OLLAMA_TIMEOUT_SECONDS=90
```

Variables importantes :

- `DATABASE_URL` : connexion Neon/PostgreSQL.
- `DEFAULT_USER_ID` : utilisateur par defaut pour le chat et Streamlit.
- `USER_ID` : utilisateur force si besoin.
- `IMPORT_API_TOKEN` : token optionnel pour proteger certains imports.
- `SESSIONS_CSV_PATH` : chemin optionnel d'import CSV.
- `AUTO_IMPORT_SESSIONS_ON_STARTUP` : active/desactive l'import CSV au demarrage.
- `SESSIONS_CSV_POLL_SECONDS` : intervalle de polling CSV. `0` desactive le worker.
- `OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS` : configuration LLM local.

Ne pas remettre de token Hugging Face dans `.env` si le projet ne l'utilise pas.

## Lancer le backend

Depuis la racine du projet :

```bash
cd HealthCoachBackend
venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

URLs utiles :

- `http://localhost:8000` depuis le Mac
- `http://IP_DU_MAC:8000` depuis l'iPhone
- exemple actuel : `http://192.168.1.165:8000`

L'app iOS doit utiliser la meme adresse dans :

```text
HealthRunTracker/HealthRunTracker/App/APIConfig.swift
```

## Lancer Streamlit

Depuis `HealthCoachBackend` :

```bash
venv/bin/streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0
```

URLs utiles :

- `http://localhost:8501`
- `http://IP_DU_MAC:8501`

Streamlit lit les donnees depuis Neon quand `DATABASE_URL` et l'utilisateur sont configures. Sinon, il peut retomber sur un CSV local si disponible.

## Structure du code

```text
HealthCoachBackend/
├── api/                 # Routes FastAPI
├── core/
│   ├── models/          # Modeles SQLAlchemy
│   ├── services/        # Services metier
│   ├── metrics/         # Definition des metriques DB
│   ├── config.py        # Lecture .env
│   └── heart_rate_zones.py
├── execution/           # Execution des intentions
├── intents/             # Detection et schemas d'intentions
├── normalization/       # Normalisation des periodes/metriques
├── recommendation/      # Recommandations et risque
├── routing/             # Routage metier et entree semantique
├── schemas/             # Schemas Pydantic API
├── streamlit_app/       # Pages Streamlit
├── verbalization/       # Transformation en reponses lisibles
├── database.py          # Connexion SQLAlchemy
└── main.py              # Entree FastAPI
```

## Routes principales

- `GET /` : verification simple du backend.
- `GET /health/db` : verification de la connexion Neon.
- `GET /debug/tables` : liste les tables accessibles.
- `POST /chat` : point d'entree du coach conversationnel.
- `POST /api/run-session` : ingestion d'une seance.
- `POST /api/run-sessions/batch` : ingestion par lots depuis l'app iOS.
- `GET /api/run-sessions` : lecture des seances sur une periode.
- `POST /api/import/apple-health` : import Apple Health JSON.
- `POST /api/upload-sessions-csv` : import CSV.
- `GET /api/signature` : lecture/calcul de la signature coureur.

L'ancienne route snapshot a ete retiree. Neon est maintenant la source persistante ; les resumes, metriques et comparaisons sont recalcules depuis la base.

## Synchronisation iOS vers Neon

Flux principal :

1. L'app iOS lit les workouts HealthKit.
2. Elle filtre les seances invalides.
3. Elle envoie les donnees vers `POST /api/run-sessions/batch`.
4. Le backend fait un upsert par `(user_id, start_time)`.
5. Les semaines `RunWeek` sont reconstruites pour l'utilisateur touche.
6. La signature coureur est invalidee pour etre recalculee a la prochaine demande.

Fichiers importants :

```text
api/runs.py
core/models/RunSession.py
core/models/RunWeek.py
core/services/run_weeks/builder.py
core/services/signature/signature_store.py
schemas/schemas.py
```

Une synchronisation reussie apparait dans les logs :

```text
POST /api/run-sessions/batch HTTP/1.1 200 OK
```

## Zones cardiaques

Les zones cardiaques cote Python sont centralisees ici :

```text
core/heart_rate_zones.py
```

Valeurs actuelles :

- `Z1` : `< 145 bpm`
- `Z2` : `145-158 bpm`
- `Z3` : `159-172 bpm`
- `Z4` : `173-185 bpm`
- `Z5` : `>= 186 bpm`

Si les seuils changent, modifier ce fichier cote backend et le fichier equivalent cote iOS :

```text
HealthRunTracker/HealthRunTracker/Core/HeartRateZones.swift
```

## Chat et logique metier

Le chat ne lit pas directement une table de snapshots.

Flux actuel :

1. `api/chat.py` recoit la question.
2. `intents/intent_detector.py` detecte l'intention.
3. `routing/router.py` route vers le bon executor.
4. `execution/*` calcule les faits depuis Neon.
5. `verbalization/verbalizer.py` transforme les faits en reponse lisible.

Types de demandes gerees :

- metrique simple : distance, duree, denivele, frequence cardiaque moyenne
- comparaison de periodes
- bilan de periode
- coaching : regularite, volume, charge, progression
- recommandation

## Recommandations et signatures

La signature coureur represente l'historique long-terme.

Fichiers principaux :

```text
core/services/signature/builder.py
core/services/signature/signature_service.py
core/services/signature/signature_store.py
recommendation/engine.py
recommendation/current_week.py
recommendation/risk.py
```

Quand de nouvelles seances sont ingerees, la signature est invalidee pour eviter d'utiliser une ancienne analyse.

## Verification rapide

Compilation Python :

```bash
cd HealthCoachBackend
venv/bin/python -m compileall core api schemas execution routing recommendation coaching normalization intents verbalization streamlit_app
```

Backend et DB :

```bash
curl http://localhost:8000/health/db
```

Resultat attendu :

```json
{"db":"ok"}
```

Verification des routes d'ingestion :

```bash
curl -s http://localhost:8000/openapi.json | venv/bin/python -c 'import json,sys; p=json.load(sys.stdin)["paths"]; print("/api/run-session" in p, "/api/run-sessions/batch" in p)'
```

Resultat attendu :

```text
True True
```

Streamlit :

```bash
curl -I http://localhost:8501
```

Resultat attendu : `HTTP/1.1 200 OK`.

## Points d'attention

- Ne jamais committer `.env`.
- Garder `.env.example` vide de secrets.
- Apres modification des routes, verifier `/openapi.json`.
- Apres modification de l'ingestion, verifier que l'iPhone envoie toujours `POST /api/run-sessions/batch`.
- Apres modification des zones cardiaques, verifier `core/heart_rate_zones.py`, Streamlit et `HeartRateZones.swift`.
- Le backend doit ecouter sur `0.0.0.0` pour etre joignable depuis l'iPhone.
