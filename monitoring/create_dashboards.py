#!/usr/bin/env python3
"""
create_dashboards.py - Automatisierte Erstellung und Verwaltung von Grafana-Dashboards.

Dieses Skript:
1. Prüft die Verbindung zu Grafana.
2. Erkennt dynamisch die Prometheus-Datenquelle (oder legt sie automatisch an).
3. Erstellt bzw. aktualisiert 3 produktionsreife Dashboards:
   - 🎬 Content Pipeline Monitoring (Status, Laufzeit, Workflow-Gesundheit)
   - 🎬 Content Production & Pipeline Operations (Shorts vs. Long, Service-Laufzeiten)
   - 💰 Cloud & Microservice Cost Explorer (FinOps, VM-Kosten, API-Stückkosten)
4. Ersetzt alle Datenquellen-UIDs dynamisch, sodass keine Werte hardkodiert sind.

Verwendung:
    # Lokal mit Docker (Standardwerte):
    python monitoring/create_dashboards.py

    # Remote mit Argumenten:
    python monitoring/create_dashboards.py --grafana-url http://<IP>:3000 --user admin --password admin

    # Oder per Umgebungsvariablen:
    export GRAFANA_URL="http://<IP>:3000"
    export GRAFANA_USER="admin"
    export GRAFANA_PASSWORD="admin"
    python monitoring/create_dashboards.py
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

# UTF-8 Ausgabe für Windows PowerShell / CMD sicherstellen
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_auth_headers(user: str, password: str) -> dict:
    """Erstellt Basic-Auth-Header für die Grafana REST API."""
    creds = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def check_grafana_health(grafana_url: str) -> bool:
    """Prüft, ob Grafana erreichbar und betriebsbereit ist."""
    url = f"{grafana_url.rstrip('/')}/api/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            version = data.get("version", "unbekannt")
            print(f"✅ Verbindung zu Grafana erfolgreich ({grafana_url}, Version {version})")
            return True
    except Exception as exc:
        print(f"❌ Fehler bei Verbindung zu Grafana ({url}): {exc}", file=sys.stderr)
        return False


def ensure_prometheus_datasource(grafana_url: str, headers: dict, prometheus_url: str) -> str:
    """
    Prüft, ob eine Prometheus-Datenquelle in Grafana existiert.
    Falls nicht, wird sie automatisch über die REST API angelegt.
    Gibt die dynamische Datasource-UID zurück.
    """
    url = f"{grafana_url.rstrip('/')}/api/datasources"
    
    # 1. Vorhandene Datenquellen auflisten
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            datasources = json.loads(resp.read().decode("utf-8"))
            for ds in datasources:
                if ds.get("type") == "prometheus":
                    uid = ds.get("uid")
                    name = ds.get("name")
                    print(f"ℹ️ Vorhandene Prometheus-Datenquelle gefunden: '{name}' (UID: {uid})")
                    return uid
    except Exception as exc:
        print(f"⚠️ Warnung beim Abfragen existierender Datenquellen: {exc}", file=sys.stderr)

    # 2. Falls nicht vorhanden: Automatisch anlegen
    print(f"⚙️ Erstelle neue Prometheus-Datenquelle mit URL '{prometheus_url}'...")
    payload = {
        "name": "Prometheus",
        "type": "prometheus",
        "access": "proxy",
        "url": prometheus_url,
        "isDefault": True,
    }
    req_create = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req_create, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            uid = res.get("datasource", {}).get("uid") or res.get("uid", "prometheus-auto")
            print(f"✅ Prometheus-Datenquelle erfolgreich erstellt (UID: {uid})")
            return uid
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        print(f"❌ Fehler beim Erstellen der Datenquelle (HTTP {err.code}): {body}", file=sys.stderr)
        raise


def inject_datasource_uid(obj, ds_uid: str):
    """Durchläuft das Dashboard-Dictionary rekursiv und ersetzt Datenquellen-UIDs."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "datasource" and isinstance(v, dict):
                v["uid"] = ds_uid
            else:
                inject_datasource_uid(v, ds_uid)
    elif isinstance(obj, list):
        for item in obj:
            inject_datasource_uid(item, ds_uid)


def publish_dashboard(grafana_url: str, headers: dict, dashboard_data: dict, ds_uid: str) -> str:
    """Veröffentlicht ein Dashboard in Grafana und gibt die relative URL zurück."""
    # Datenquellen-UID dynamisch in allen Panels setzen
    inject_datasource_uid(dashboard_data, ds_uid)

    payload = {
        "dashboard": dashboard_data,
        "overwrite": True,
    }

    url = f"{grafana_url.rstrip('/')}/api/dashboards/db"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        dash_url = res.get("url", "")
        title = dashboard_data.get("title", "Dashboard")
        full_url = f"{grafana_url.rstrip('/')}{dash_url}"
        print(f"✅ Dashboard '{title}' bereitgestellt: {full_url}")
        return full_url


# =============================================================================
# Dashboard-Definitionen (Ohne hardcodierte UIDs oder IPs)
# =============================================================================

def get_starter_dashboard() -> dict:
    """1. Content Pipeline Monitoring (Starter & Workflow Health Overview)"""
    return {
        "id": None,
        "uid": "pipeline-starter",
        "title": "🎬 Content Pipeline Monitoring",
        "tags": ["pipeline", "github-actions", "health"],
        "timezone": "browser",
        "refresh": "10s",
        "panels": [
            {
                "id": 1,
                "title": "Pipeline Status (Letzter Run)",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_status",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "mappings": [
                            {
                                "type": "value",
                                "options": {
                                    "1": {"text": "ERFOLGREICH / ONLINE", "color": "green"},
                                    "0": {"text": "FEHLGESCHLAGEN", "color": "red"},
                                },
                            }
                        ]
                    }
                },
            },
            {
                "id": 2,
                "title": "Letzte Run-Nummer",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_latest_run_number",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "none",
                        "color": {"fixedColor": "#73BF69", "mode": "fixed"},
                    }
                },
            },
            {
                "id": 3,
                "title": "Pipeline Laufzeit (Letzter Durchlauf)",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_duration_seconds",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "s",
                        "color": {"mode": "thresholds"},
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"value": 0, "color": "green"},
                                {"value": 240, "color": "yellow"},
                                {"value": 400, "color": "red"},
                            ],
                        },
                    }
                },
            },
            {
                "id": 4,
                "title": "Erfolgsquote aller Runs",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_success_rate_percent",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "color": {"mode": "thresholds"},
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"value": 0, "color": "red"},
                                {"value": 70, "color": "yellow"},
                                {"value": 85, "color": "green"},
                            ],
                        },
                    }
                },
            },
            {
                "id": 5,
                "title": "Laufzeit aller GitHub Workflow-Runs (in Sekunden)",
                "type": "barchart",
                "gridPos": {"h": 9, "w": 16, "x": 0, "y": 5},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_run_duration_seconds",
                        "legendFormat": "#{{run_number}} ({{conclusion}})",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "s",
                        "color": {"mode": "palette-classic"},
                    }
                },
            },
            {
                "id": 6,
                "title": "Status aller Durchläufe",
                "type": "piechart",
                "gridPos": {"h": 9, "w": 8, "x": 16, "y": 5},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'github_workflow_runs_total{conclusion=~"success|failure|cancelled"}',
                        "legendFormat": "{{conclusion}}",
                        "refId": "A",
                    }
                ],
                "options": {
                    "legend": {"displayMode": "table", "placement": "right", "values": ["value", "percent"]}
                },
            },
            {
                "id": 7,
                "title": "Tabelle aller Workflow-Runs (Detailübersicht)",
                "type": "table",
                "gridPos": {"h": 10, "w": 24, "x": 0, "y": 14},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_run_duration_seconds",
                        "format": "table",
                        "instant": True,
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "custom": {
                            "align": "auto",
                            "displayMode": "auto",
                        }
                    },
                    "overrides": [
                        {
                            "matcher": {"id": "byName", "options": "Value"},
                            "properties": [
                                {"id": "unit", "value": "s"},
                                {"id": "displayName", "value": "Dauer (Sekunden)"},
                            ],
                        }
                    ],
                },
            },
        ],
    }


def get_pipeline_ops_dashboard() -> dict:
    """2. Content Production & Pipeline Operations (Deep Dive)"""
    return {
        "id": None,
        "uid": "pipeline-ops",
        "title": "🎬 Content Production & Pipeline Operations",
        "tags": ["pipeline", "operations", "production"],
        "timezone": "browser",
        "refresh": "10s",
        "panels": [
            {
                "id": 1,
                "title": "Gesamtanzahl Videos",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'project_total_videos_created{type="total"}',
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "color": {"fixedColor": "#3274D9", "mode": "fixed"},
                        "unit": "none",
                    }
                },
            },
            {
                "id": 2,
                "title": "YouTube Shorts",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'project_total_videos_created{type="shorts"}',
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "color": {"fixedColor": "#FF9830", "mode": "fixed"},
                        "unit": "none",
                    }
                },
            },
            {
                "id": 3,
                "title": "Long-Form Videos",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'project_total_videos_created{type="long"}',
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "color": {"fixedColor": "#B877D9", "mode": "fixed"},
                        "unit": "none",
                    }
                },
            },
            {
                "id": 4,
                "title": "Pipeline Status",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_status",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "mappings": [
                            {
                                "type": "value",
                                "options": {
                                    "1": {"text": "ONLINE / ERFOLGREICH", "color": "green"},
                                    "0": {"text": "FEHLGESCHLAGEN", "color": "red"},
                                },
                            }
                        ]
                    }
                },
            },
            {
                "id": 5,
                "title": "Pipeline Ausführungsdauer (Verlauf in Sekunden)",
                "type": "timeseries",
                "gridPos": {"h": 9, "w": 15, "x": 0, "y": 5},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "github_workflow_duration_seconds",
                        "legendFormat": "{{workflow}}",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "s",
                        "custom": {
                            "lineInterpolation": "smooth",
                            "fillOpacity": 20,
                            "pointSize": 5,
                            "showPoints": "auto",
                        },
                    }
                },
            },
            {
                "id": 6,
                "title": "Format-Verteilung (Shorts vs. Long)",
                "type": "piechart",
                "gridPos": {"h": 9, "w": 9, "x": 15, "y": 5},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'project_total_videos_created{type=~"shorts|long"}',
                        "legendFormat": "{{type}}",
                        "refId": "A",
                    }
                ],
                "options": {
                    "legend": {
                        "displayMode": "table",
                        "placement": "right",
                        "values": ["value", "percent"],
                    }
                },
            },
            {
                "id": 7,
                "title": "Durchschnittliche Bearbeitungsdauer pro Microservice (Sekunden)",
                "type": "bargauge",
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 14},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "microservice_execution_seconds_average",
                        "legendFormat": "{{service}}",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "s",
                        "color": {"mode": "thresholds"},
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"value": 0, "color": "green"},
                                {"value": 25, "color": "yellow"},
                                {"value": 40, "color": "orange"},
                                {"value": 50, "color": "red"},
                            ],
                        },
                    }
                },
                "options": {
                    "orientation": "horizontal",
                    "displayMode": "gradient",
                },
            },
        ],
    }


def get_finops_dashboard() -> dict:
    """3. Cloud & Microservice Cost Explorer (FinOps)"""
    return {
        "id": None,
        "uid": "cost-finops",
        "title": "💰 Cloud & Microservice Cost Explorer (FinOps)",
        "tags": ["costs", "finops", "gcp", "apis"],
        "timezone": "browser",
        "refresh": "30s",
        "panels": [
            {
                "id": 1,
                "title": "GCP VM Monatskosten (e2-small Frankfurt)",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 0, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'gcp_vm_cost_dollars{period="monthly"}',
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "color": {"fixedColor": "#3274D9", "mode": "fixed"},
                    }
                },
            },
            {
                "id": 2,
                "title": "Kosten pro Short Video (Gesamt)",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 6, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'unit_economics_video_cost_dollars{type=~".*Shorts.*"}',
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "color": {"fixedColor": "#56A64B", "mode": "fixed"},
                    }
                },
            },
            {
                "id": 3,
                "title": "Kosten pro Long-Form Video (Gesamt)",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 12, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'unit_economics_video_cost_dollars{type=~".*Long-Form.*"}',
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "color": {"fixedColor": "#E0B400", "mode": "fixed"},
                    }
                },
            },
            {
                "id": 4,
                "title": "Kumulierte API-Ausgaben (Alle Videos)",
                "type": "stat",
                "gridPos": {"h": 5, "w": 6, "x": 18, "y": 0},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'cumulative_api_spend_dollars{category="Total Production Spend"}',
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "color": {"fixedColor": "#FF780A", "mode": "fixed"},
                    }
                },
            },
            {
                "id": 5,
                "title": "Microservice Kosten pro Durchlauf (YouTube Shorts)",
                "type": "barchart",
                "gridPos": {"h": 9, "w": 12, "x": 0, "y": 5},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "microservice_cost_per_short_dollars",
                        "legendFormat": "{{service}}",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                    }
                },
            },
            {
                "id": 6,
                "title": "Microservice Kosten pro Durchlauf (Long-Form Videos)",
                "type": "barchart",
                "gridPos": {"h": 9, "w": 12, "x": 12, "y": 5},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "microservice_cost_per_long_dollars",
                        "legendFormat": "{{service}}",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                    }
                },
            },
            {
                "id": 7,
                "title": "Bisherige API-Kosten nach Provider (Gemini vs. Vertex AI vs. ElevenLabs)",
                "type": "piechart",
                "gridPos": {"h": 9, "w": 12, "x": 0, "y": 14},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": 'cumulative_api_spend_dollars{category!~"Total.*"}',
                        "legendFormat": "{{category}}",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                    }
                },
                "options": {
                    "legend": {
                        "displayMode": "table",
                        "placement": "right",
                        "values": ["value", "percent"],
                    }
                },
            },
            {
                "id": 8,
                "title": "GCP VM Infrastruktur Kostenübersicht",
                "type": "bargauge",
                "gridPos": {"h": 9, "w": 12, "x": 12, "y": 14},
                "targets": [
                    {
                        "datasource": {"type": "prometheus", "uid": "auto"},
                        "expr": "gcp_vm_cost_dollars",
                        "legendFormat": "{{period}}",
                        "refId": "A",
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "currencyUSD",
                        "color": {"mode": "palette-classic"},
                    }
                },
                "options": {
                    "orientation": "horizontal",
                    "displayMode": "gradient",
                },
            },
        ],
    }


# =============================================================================
# Hauptprogramm
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Automatisierte Erstellung und Verwaltung von Grafana-Dashboards & Datenquellen."
    )
    parser.add_argument(
        "--grafana-url",
        default=os.environ.get("GRAFANA_URL", "http://localhost:3000"),
        help="Basis-URL von Grafana (Standard: $GRAFANA_URL oder http://localhost:3000)",
    )
    parser.add_argument(
        "--user",
        default=os.environ.get("GRAFANA_USER", "admin"),
        help="Grafana Benutzername (Standard: $GRAFANA_USER oder admin)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("GRAFANA_PASSWORD", "admin"),
        help="Grafana Passwort (Standard: $GRAFANA_PASSWORD oder admin)",
    )
    parser.add_argument(
        "--prometheus-url",
        default=os.environ.get("PROMETHEUS_URL", "http://prometheus:9090"),
        help="Prometheus Server URL für Grafana (Standard: $PROMETHEUS_URL oder http://prometheus:9090)",
    )

    args = parser.parse_args()

    print("=" * 65)
    print("🚀 Starte Grafana Dashboard & Datasource Provisioning")
    print("=" * 65)
    print(f"📍 Grafana URL:    {args.grafana_url}")
    print(f"👤 Benutzer:       {args.user}")
    print(f"📡 Prometheus URL: {args.prometheus_url}")
    print("-" * 65)

    headers = get_auth_headers(args.user, args.password)

    # 1. Verbindung prüfen
    if not check_grafana_health(args.grafana_url):
        sys.exit(1)

    # 2. Prometheus Datenquelle auflösen / anlegen
    ds_uid = ensure_prometheus_datasource(args.grafana_url, headers, args.prometheus_url)

    # 3. Alle Dashboards publizieren
    dashboards = [
        ("1/3", get_starter_dashboard()),
        ("2/3", get_pipeline_ops_dashboard()),
        ("3/3", get_finops_dashboard()),
    ]

    deployed_urls = []
    print("-" * 65)
    print("📦 Publizieren der Dashboards:")
    for idx, dash in dashboards:
        print(f"[{idx}] {dash['title']}...")
        url = publish_dashboard(args.grafana_url, headers, dash, ds_uid)
        deployed_urls.append((dash['title'], url))

    print("=" * 65)
    print("🎉 Alle Dashboards erfolgreich bereitgestellt!")
    print("=" * 65)
    for title, url in deployed_urls:
        print(f"➡️  {title}:")
        print(f"    {url}")
    print("=" * 65)


if __name__ == "__main__":
    main()
