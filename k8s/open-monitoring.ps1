# open-monitoring.ps1 - Port-Forwarding fuer Grafana, Prometheus und Pushgateway
param (
    [string]$Service = "grafana"
)

# Grafana Admin Passwort auslesen
$b64 = kubectl get secret --namespace monitoring k8s-monitoring-grafana -o jsonpath="{.data.admin-password}"
$adminPw = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($b64))

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Kubernetes Monitoring Stack (Minikube)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Grafana Login:    admin" -ForegroundColor Yellow
Write-Host "Grafana Passwort: $adminPw" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------"

switch ($Service.ToLower()) {
    "prometheus" {
        Write-Host "Starte Port-Forward fuer Prometheus auf http://localhost:9090..." -ForegroundColor Green
        kubectl port-forward svc/k8s-monitoring-kube-promet-prometheus -n monitoring 9090:9090
    }
    "pushgateway" {
        Write-Host "Starte Port-Forward fuer Pushgateway auf http://localhost:9091..." -ForegroundColor Green
        kubectl port-forward svc/pushgateway -n monitoring 9091:9091
    }
    default {
        Write-Host "Starte Port-Forward fuer Grafana auf http://localhost:3000..." -ForegroundColor Green
        Write-Host "Oeffne deinen Browser unter: http://localhost:3000" -ForegroundColor Cyan
        kubectl port-forward svc/k8s-monitoring-grafana -n monitoring 3000:80
    }
}
