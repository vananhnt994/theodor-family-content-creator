#!/usr/bin/env bash
# setup-secrets.sh - Erstellt Kubernetes-Secrets aus lokalen .env und Google JSON-Dateien
set -e

NAMESPACE="${1:-content-creator}"
echo "🔐 Konfiguriere Kubernetes-Secrets im Namespace '$NAMESPACE'..."

# 1. API-Schlüssel aus .env importieren
if [ -f ".env" ]; then
    echo "📄 .env Datei gefunden. Erstelle 'content-creator-secrets'..."
    kubectl create secret generic content-creator-secrets \
        --namespace "$NAMESPACE" \
        --from-env-file=.env \
        --dry-run=client -o yaml | kubectl apply -f -
else
    echo "⚠️ Keine .env Datei im aktuellen Verzeichnis gefunden!"
fi

# 2. Google Tokens & Credentials importieren
GOOGLE_ARGS=()
[ -f "credentials.json" ] && GOOGLE_ARGS+=("--from-file=credentials.json=credentials.json")
[ -f "token.json" ] && GOOGLE_ARGS+=("--from-file=token.json=token.json")
[ -f "drive_token.json" ] && GOOGLE_ARGS+=("--from-file=drive_token.json=drive_token.json")

if [ ${#GOOGLE_ARGS[@]} -gt 0 ]; then
    echo "🔑 Google Token-Dateien gefunden (${#GOOGLE_ARGS[@]}). Erstelle 'content-creator-google-tokens'..."
    kubectl create secret generic content-creator-google-tokens \
        --namespace "$NAMESPACE" \
        "${GOOGLE_ARGS[@]}" \
        --dry-run=client -o yaml | kubectl apply -f -
fi

echo "✅ Secrets erfolgreich konfiguriert!"
kubectl get secrets -n "$NAMESPACE"
