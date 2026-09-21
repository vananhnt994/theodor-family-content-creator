# ☸️ Kubernetes & Helm Architektur: Theodor Family Content Creator

Dieses Verzeichnis enthält alle Kubernetes-Manifeste und Automatisierungsskripte für den Betrieb der Content-Pipeline in einem lokalen **Minikube**-Cluster (oder später auf **Google Kubernetes Engine (GKE)**).

---

## 🏗️ 1. Komponenten & Namespaces

Die Anwendung ist in zwei logisch getrennte Namespaces aufgeteilt:

1. **`content-creator` (Applikation):**
   - **`PersistentVolumeClaim` (`content-creator-output-pvc`):** Persistenter 5-GB-Speicher für generierte Videos, Audio-Dateien und `historie_*.json`.
   - **`Secrets`:**
     - `content-creator-secrets`: Umgebungsvariablen (`GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, etc.).
     - `content-creator-google-tokens`: Google OAuth & Service Account JSONs (`credentials.json`, `token.json`, `drive_token.json`).
   - **`Job` (`content-creator-manual-job`):** Für manuelle Sofortausführungen.
   - **`CronJob` (`content-creator-scheduled-cronjob`):** Zeitgesteuerte Ausführung 3-mal täglich (`0 6,10,15 * * *` = 08:00, 12:00, 17:00 Uhr deutsche Zeit).

2. **`monitoring` (Monitoring-Stack via Helm):**
   - **`kube-prometheus-stack`:** Prometheus Operator, Prometheus TSDB, Grafana, Alertmanager, Node-Exporter, Kube-State-Metrics.
   - **`pushgateway`:** Empfängt Pipeline-Metriken aus den kurzlebigen Kubernetes-Jobs.

---

## 🚀 2. Schnellanleitung & Wichtigste Befehle

### A. Pipeline manuell starten (Ad-hoc Job)
Um einen Video-Rendering-Lauf sofort manuell zu starten:

```powershell
# Option 1: Neuen Job direkt aus dem CronJob klonen
kubectl create job --from=cronjob/content-creator-scheduled-cronjob manual-test-1 -n content-creator

# Option 2: Über das Manifest starten
kubectl apply -f k8s/job-pipeline.yaml

# Live-Logs des laufenden Jobs verfolgen:
kubectl logs -f job/content-creator-manual-job -n content-creator
```

### B. Geplante CronJobs verwalten
```powershell
# Status der CronJobs abfragen:
kubectl get cronjobs -n content-creator

# Historie der letzten Jobs anzeigen:
kubectl get jobs -n content-creator
```

### C. Monitoring aufrufen (Grafana & Prometheus)
Nutze das mitgelieferte Hilfsskript:

```powershell
# 1. Grafana starten (Port 3000):
.\k8s\open-monitoring.ps1

# 2. Prometheus Expression Browser starten (Port 9090):
.\k8s\open-monitoring.ps1 -Service prometheus

# 3. Pushgateway starten (Port 9091):
.\k8s\open-monitoring.ps1 -Service pushgateway
```
*Das Skript ermittelt automatisch das aktuelle Grafana-Admin-Passwort und öffnet den Port auf `localhost`!*

### D. Neues Docker-Image nach Codeänderungen bauen
Wenn du Änderungen am Python-Code vornimmst:

```powershell
# 1. Image neu bauen
docker build -t content-creator:local .

# 2. Direkt in Minikube übertragen
minikube image load content-creator:local
```

### E. Secrets aktualisieren
Wenn du API-Schlüssel in deiner `.env` änderst:

```powershell
.\k8s\setup-secrets.ps1
```

---

## 📂 Dateiübersicht

| Datei | Beschreibung |
| :--- | :--- |
| `namespace.yaml` | Erstellt den Namespace `content-creator` |
| `pvc.yaml` | 5GB Speicher für Videos & Historie (`output/`) |
| `job-pipeline.yaml` | Kubernetes Job Manifest für Einzel-Durchläufe |
| `cronjob-pipeline.yaml` | Kubernetes CronJob für automatische 3x tägliche Läufe |
| `pushgateway.yaml` | Cluster-interner Metriken-Puffer |
| `setup-secrets.ps1` / `.sh` | Sicheres Einlesen lokaler Secrets in K8s |
| `open-monitoring.ps1` / `.sh` | Bequemer Zugriff auf Grafana/Prometheus via Port-Forwarding |
