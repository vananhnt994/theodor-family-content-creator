#!/usr/bin/env python3
"""
create_dashboards.py - Creates Grafana Dashboards for:
1. 🎬 Content Production & Pipeline Operations
2. 💰 Cloud & Microservice Cost Explorer (FinOps)
"""

import base64
import json
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def create_dashboards():
    grafana_url = "http://<MONITORING_VM_IP>:3000"
    creds = base64.b64encode(b"admin:admin").decode("ascii")
    headers = {
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/json",
    }

    # -------------------------------------------------------------
    # 1. Pipeline Operations Dashboard
    # -------------------------------------------------------------
    dash_ops = {
        "dashboard": {
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
        },
        "overwrite": True,
    }

    req1 = urllib.request.Request(
        f"{grafana_url}/api/dashboards/db",
        data=json.dumps(dash_ops).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req1) as resp:
        res1 = json.loads(resp.read().decode("utf-8"))
        print(f"✅ Dashboard 1 erstellt: {grafana_url}{res1.get('url')}")

    # -------------------------------------------------------------
    # 2. Cloud & FinOps Cost Explorer Dashboard
    # -------------------------------------------------------------
    dash_finops = {
        "dashboard": {
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                    "title": "Kumulierte API-Ausgaben (Alle 23 Videos)",
                    "type": "stat",
                    "gridPos": {"h": 5, "w": 6, "x": 18, "y": 0},
                    "targets": [
                        {
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
                            "datasource": {"uid": "afyrbxkjyhkhse"},
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
        },
        "overwrite": True,
    }

    req2 = urllib.request.Request(
        f"{grafana_url}/api/dashboards/db",
        data=json.dumps(dash_finops).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req2) as resp:
        res2 = json.loads(resp.read().decode("utf-8"))
        print(f"✅ Dashboard 2 erstellt: {grafana_url}{res2.get('url')}")


if __name__ == "__main__":
    create_dashboards()
