#!/usr/bin/env bash
# open-monitoring.sh - Port-Forwarding fuer Grafana, Prometheus und Pushgateway
SERVICE="${1:-grafana}"

ADMIN_PW=$(kubectl get secret --namespace monitoring k8s-monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 -d)

echo "=========================================================="
echo "Kubernetes Monitoring Stack (Minikube)"
echo "=========================================================="
echo "Grafana Login:    admin"
echo "Grafana Passwort: $ADMIN_PW"
echo "----------------------------------------------------------"

if [ "$SERVICE" = "prometheus" ]; then
    echo "Starte Port-Forward fuer Prometheus auf http://localhost:9090..."
    kubectl port-forward svc/k8s-monitoring-kube-promet-prometheus -n monitoring 9090:9090
elif [ "$SERVICE" = "pushgateway" ]; then
    echo "Starte Port-Forward fuer Pushgateway auf http://localhost:9091..."
    kubectl port-forward svc/pushgateway -n monitoring 9091:9091
else
    echo "Starte Port-Forward fuer Grafana auf http://localhost:3000..."
    echo "Oeffne deinen Browser unter: http://localhost:3000"
    kubectl port-forward svc/k8s-monitoring-grafana -n monitoring 3000:80
fi
