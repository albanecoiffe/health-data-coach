#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/HealthCoachBackend"
IOS_DIR="$ROOT_DIR/HealthRunTracker"
HOSTNAME="${HEALTHCOACH_HOSTNAME:-MacBook-Pro-de-Albane.local}"
PORT="${HEALTHCOACH_PORT:-8000}"
BASE_URL="http://$HOSTNAME:$PORT"
BACKEND_LOG="$BACKEND_DIR/.dev_backend.log"
XCODE_DEV_DIR="${DEVELOPER_DIR:-/Applications/Xcode.app/Contents/Developer}"
PROJECT="$IOS_DIR/HealthRunTracker.xcodeproj"
SCHEME="${HEALTHCOACH_SCHEME:-HealthRunTracker}"
DERIVED_DATA_PATH="${HEALTHCOACH_DERIVED_DATA:-/tmp/HealthCoachDerivedData}"
APP_PATH="$DERIVED_DATA_PATH/Build/Products/Debug-iphoneos/HealthRunTracker.app"
ALLOW_PROVISIONING_UPDATES="${HEALTHCOACH_ALLOW_PROVISIONING_UPDATES:-1}"
REQUIRE_DEVICE_SUCCESS="${HEALTHCOACH_REQUIRE_DEVICE_SUCCESS:-0}"

echo "Backend URL: $BASE_URL"

find_iphone_device_id() {
  DEVELOPER_DIR="$XCODE_DEV_DIR" xcrun devicectl list devices |
    grep -E 'iPhone|Iphone' |
    grep 'available (paired)' |
    sed -E 's/.* ([0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}) .*/\1/' |
    head -n 1
}

run_with_retry() {
  local label="$1"
  shift
  local attempts="${HEALTHCOACH_DEVICE_RETRIES:-3}"
  local delay="${HEALTHCOACH_DEVICE_RETRY_DELAY:-4}"
  local attempt

  for attempt in $(seq 1 "$attempts"); do
    echo "$label tentative $attempt/$attempts..."
    if "$@"; then
      return 0
    fi

    if [[ "$attempt" -lt "$attempts" ]]; then
      echo "$label a echoue. Deverrouille l'iPhone et garde-le branche; nouvelle tentative dans ${delay}s."
      sleep "$delay"
    fi
  done

  return 1
}

if [[ ! -x "$BACKEND_DIR/venv/bin/python" ]]; then
  echo "Backend venv introuvable: $BACKEND_DIR/venv/bin/python"
  exit 1
fi

existing_pid="$(lsof -tiTCP:"$PORT" -sTCP:LISTEN || true)"
if [[ -n "$existing_pid" ]]; then
  echo "Arret du backend existant sur le port $PORT: $existing_pid"
  kill "$existing_pid" || true
  sleep 1
fi

echo "Demarrage backend..."
(
  cd "$BACKEND_DIR"
  nohup "$BACKEND_DIR/venv/bin/python" -m uvicorn main:app --host 0.0.0.0 --port "$PORT" > "$BACKEND_LOG" 2>&1 &
  echo "$!" > "$BACKEND_DIR/.dev_backend.pid"
)
backend_pid="$(cat "$BACKEND_DIR/.dev_backend.pid")"
disown "$backend_pid" 2>/dev/null || true
echo "Backend PID: $backend_pid"
echo "Logs backend: $BACKEND_LOG"

for _ in {1..30}; do
  if curl -fsS "$BASE_URL/health/db" >/dev/null 2>&1; then
    echo "Backend OK: $BASE_URL/health/db"
    break
  fi
  sleep 1
done

if ! curl -fsS "$BASE_URL/health/db" >/dev/null 2>&1; then
  echo "Backend inaccessible apres 30s."
  tail -80 "$BACKEND_LOG" || true
  exit 1
fi

echo "Build iOS..."
XCODEBUILD_ARGS=(
  -project "$PROJECT"
  -scheme "$SCHEME"
  -configuration Debug
  -destination generic/platform=iOS
  -derivedDataPath "$DERIVED_DATA_PATH"
)

if [[ "$ALLOW_PROVISIONING_UPDATES" == "1" ]]; then
  XCODEBUILD_ARGS+=(-allowProvisioningUpdates)
fi

DEVELOPER_DIR="$XCODE_DEV_DIR" xcodebuild \
  "${XCODEBUILD_ARGS[@]}" \
  build

if [[ ! -d "$APP_PATH" ]]; then
  echo "App build introuvable: $APP_PATH"
  exit 1
fi

device_id="${HEALTHCOACH_DEVICE_ID:-}"
if [[ -z "$device_id" ]]; then
  device_id="$(find_iphone_device_id)"
fi

if [[ -z "$device_id" ]]; then
  echo "Aucun iPhone disponible. Branche/deverrouille le telephone ou definis HEALTHCOACH_DEVICE_ID."
  DEVELOPER_DIR="$XCODE_DEV_DIR" xcrun devicectl list devices || true
  if [[ "$REQUIRE_DEVICE_SUCCESS" == "1" ]]; then
    exit 1
  fi
  echo
  echo "Pret partiellement."
  echo "Backend: $BASE_URL"
  echo "Build iOS: OK"
  echo "Installation iPhone: non effectuee"
  echo "Pour suivre les logs: tail -f '$BACKEND_LOG'"
  exit 0
fi

echo "Installation sur iPhone: $device_id"
if ! run_with_retry "Installation" env DEVELOPER_DIR="$XCODE_DEV_DIR" xcrun devicectl device install app --device "$device_id" "$APP_PATH"; then
  echo "Installation impossible via devicectl."
  echo "Actions utiles: deverrouiller l'iPhone, verifier le cable/Wi-Fi, accepter 'Faire confiance', puis relancer ./scripts/dev_phone.sh."
  if [[ "$REQUIRE_DEVICE_SUCCESS" == "1" ]]; then
    exit 1
  fi
  echo
  echo "Pret partiellement."
  echo "Backend: $BASE_URL"
  echo "Build iOS: OK"
  echo "Installation iPhone: echec devicectl"
  echo "Tu peux lancer l'app manuellement si elle est deja installee, ou faire un Run depuis Xcode."
  echo "Pour suivre les logs: tail -f '$BACKEND_LOG'"
  exit 0
fi

echo "Lancement de l'app..."
if ! run_with_retry "Lancement" env DEVELOPER_DIR="$XCODE_DEV_DIR" xcrun devicectl device process launch --device "$device_id" com.albane.health.HealthRunTracker; then
  echo "L'app est installee mais n'a pas pu etre lancee via devicectl."
  echo "Tu peux l'ouvrir manuellement sur l'iPhone."
fi

echo
echo "Pret."
echo "Backend: $BASE_URL"
echo "Pour suivre les logs: tail -f '$BACKEND_LOG'"
