# setup-secrets.ps1 - Erstellt Kubernetes-Secrets aus lokalen .env und Google JSON-Dateien
param (
    [string]$Namespace = "content-creator"
)

Write-Host "Konfiguriere Kubernetes-Secrets im Namespace '$Namespace'..." -ForegroundColor Cyan

# 1. API-Schluessel aus .env importieren
if (Test-Path ".env") {
    Write-Host ".env Datei gefunden. Erstelle 'content-creator-secrets'..." -ForegroundColor Green
    kubectl create secret generic content-creator-secrets --namespace $Namespace --from-env-file=.env --dry-run=client -o yaml | kubectl apply -f -
} else {
    Write-Host "Keine .env Datei im aktuellen Verzeichnis gefunden!" -ForegroundColor Yellow
}

# 2. Google Tokens & Credentials importieren (falls vorhanden)
$googleArgs = @()
if (Test-Path "credentials.json") { $googleArgs += "--from-file=credentials.json=credentials.json" }
if (Test-Path "token.json") { $googleArgs += "--from-file=token.json=token.json" }
if (Test-Path "drive_token.json") { $googleArgs += "--from-file=drive_token.json=drive_token.json" }

if ($googleArgs.Count -gt 0) {
    Write-Host "Google Token-Dateien gefunden ($($googleArgs.Count)). Erstelle 'content-creator-google-tokens'..." -ForegroundColor Green
    kubectl create secret generic content-creator-google-tokens --namespace $Namespace $googleArgs --dry-run=client -o yaml | kubectl apply -f -
} else {
    Write-Host "Keine Google JSON-Dateien (credentials.json/token.json) gefunden - ueberspringe Token-Secret." -ForegroundColor Gray
}

Write-Host "Secrets erfolgreich konfiguriert!" -ForegroundColor Cyan
Write-Host "Aktuelle Secrets im Namespace '$Namespace':"
kubectl get secrets -n $Namespace
