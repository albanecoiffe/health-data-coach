# HealthRunTracker

Application iOS SwiftUI du projet Health Data Coach.

Elle lit les donnees de course depuis Apple Health via HealthKit, affiche les vues semaine/annee/carte/chat, puis synchronise les seances vers le backend FastAPI et la base Neon.

## Prerequis

- macOS avec Xcode installe
- un iPhone physique pour tester HealthKit
- le backend `HealthCoachBackend` lance sur le meme reseau local
- les autorisations HealthKit acceptees au premier lancement

HealthKit ne fournit pas les vraies donnees Apple Health dans le simulateur. Pour tester les seances, les zones cardiaques et les traces GPS, utiliser l'iPhone.

## Lancer backend + app iPhone

Depuis la racine du projet :

```bash
./scripts/dev_phone.sh
```

Cette commande :

- demarre ou redemarre le backend FastAPI
- verifie `http://MacBook-Pro-de-Albane.local:8000/health/db`
- build l'app iOS en Debug
- detecte l'iPhone connecte
- installe l'app
- lance l'app

Le build utilise `/tmp/HealthCoachDerivedData` pour eviter les erreurs de signature quand le projet est dans iCloud.

## Lancer le backend seul

Depuis la racine du projet :

```bash
cd HealthCoachBackend
venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

L'app iOS appelle ensuite l'API configuree dans :

```text
HealthRunTracker/HealthRunTracker/App/APIConfig.swift
```

Configuration actuelle :

```swift
enum APIConfig {
    static let baseURL = "http://MacBook-Pro-de-Albane.local:8000"
}
```

Le hostname `.local` evite de modifier l'app quand l'adresse IP Wi-Fi du Mac change.

## Lancer l'app sur l'iPhone

Depuis Xcode :

1. Ouvrir `HealthRunTracker/HealthRunTracker.xcodeproj`
2. Selectionner le scheme `HealthRunTracker`
3. Selectionner l'iPhone physique
4. Lancer avec `Run`

En ligne de commande, adapter l'identifiant de l'iPhone si besoin :

```bash
xcodebuild \
  -project HealthRunTracker/HealthRunTracker.xcodeproj \
  -scheme HealthRunTracker \
  -configuration Debug \
  -destination 'platform=iOS,id=00008120-00146C502210201E' \
  build
```

## Synchronisation des donnees

Au lancement, l'app :

1. demande l'autorisation HealthKit si necessaire
2. charge les donnees semaine et annee
3. demande au backend la derniere seance deja stockee
4. relit seulement les seances recentes dans HealthKit, avec une marge de deux jours
5. envoie les nouveautes vers `POST /api/run-sessions/batch`

La premiere page de synchronisation manuelle a ete retiree. L'app s'ouvre directement sur la vue semaine.

Avant export, les seances sont filtrees pour eviter d'envoyer des donnees incoherentes :

- date dans le futur
- distance ou duree nulle
- valeurs infinies ou invalides
- frequence cardiaque hors plage plausible
- elevation ou calories incoherentes

La logique principale est dans :

```text
HealthRunTracker/HealthRunTracker/HealthKit/HealthManager.swift
HealthRunTracker/HealthRunTracker/Sync/RunSessionSyncService.swift
```

## Structure du code

```text
HealthRunTracker/HealthRunTracker/
├── App/
│   ├── APIConfig.swift
│   ├── HealthRunTrackerApp.swift
│   └── MainView.swift
├── Core/
│   └── UserSession.swift
├── Debug/
│   └── RunSessionDebugTools.swift
├── Features/
│   ├── Chat/
│   ├── Routes/
│   ├── Week/
│   └── Year/
├── HealthKit/
├── Models/
├── Sync/
└── Utils/
```

## Dossiers principaux

- `App/` : point d'entree SwiftUI, navigation principale, configuration API
- `Features/Week/` : ecran semaine, cartes de stats, graphiques, details de seance
- `Features/Year/` : vue annuelle et graphiques mensuels
- `Features/Routes/` : carte des traces GPS
- `Features/Chat/` : interface avec le coach backend
- `HealthKit/` : autorisations, lecture HealthKit, calculs, agregations
- `Sync/` : envoi des seances vers le backend
- `Models/` : structures de donnees partagees par les vues et l'API
- `Utils/` : helpers generiques

## Points d'attention

- Tester HealthKit sur iPhone, pas dans le simulateur.
- Garder `APIConfig.baseURL` aligne avec l'adresse IP locale du Mac.
- Verifier les logs backend apres lancement : une sync reussie affiche des `POST /api/run-sessions/batch` avec un status `200 OK`.
- Eviter de modifier en meme temps la lecture HealthKit et l'export Neon sans recompiler et tester sur l'iPhone.
- La vue semaine depend de `weeklyZoneBreakdown` pour le graphe des zones cardiaques par seance.

## Verification rapide

```bash
xcodebuild \
  -project HealthRunTracker/HealthRunTracker.xcodeproj \
  -scheme HealthRunTracker \
  -configuration Debug \
  -destination 'platform=iOS,id=00008120-00146C502210201E' \
  build
```

Puis lancer l'app sur l'iPhone et verifier :

- l'ouverture directe sur la vue semaine
- la presence des donnees HealthKit
- le graphe des zones cardiaques dans la vue semaine
- les logs backend de synchronisation automatique
