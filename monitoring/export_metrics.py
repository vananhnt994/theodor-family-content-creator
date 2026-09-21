#!/usr/bin/env python3
"""
export_metrics.py - Dynamischer Monitoring- & FinOps-Exporter.

Ruft automatisch und dynamisch echte GitHub Actions Workflow-Runs über die GitHub REST API ab,
aggregiert Projektstatistiken (erstellte Videos) und Kosten (VM + APIs)
und pusht alle Metriken an das Prometheus Pushgateway.
"""

import argparse
import base64
from datetime import datetime
import json
import os
import sys
import time
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Cost Constants (USD)
GCP_VM_HOURLY = 0.02083  # e2-small in europe-west3
GCP_VM_DISK_MONTHLY = 0.40  # 10 GB standard persistent disk
GCP_VM_MONTHLY = (GCP_VM_HOURLY * 730) + GCP_VM_DISK_MONTHLY  # ~$15.60
GCP_VM_DAILY = GCP_VM_MONTHLY / 30.0


def fetch_github_actions_metrics(repo: str = "vananhnt994/theodor-family-content-creator", limit: int = 50) -> list:
    """
    Ruft dynamisch die echten Workflow-Runs aus der GitHub Actions REST API ab
    und erzeugt detaillierte Prometheus-Metriken fuer jeden einzelnen Run.
    """
    url = f"https://api.github.com/repos/{repo}/actions/runs?per_page={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Monitoring-Exporter"})
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        req.add_header("Authorization", f"Bearer {github_token}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"⚠️ Warnung beim Abrufen der GitHub Actions API: {exc}", file=sys.stderr)
        return []

    runs = data.get("workflow_runs", [])
    total_count = data.get("total_count", len(runs))
    if not runs:
        return []

    def sanitize(val: str) -> str:
        return str(val).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()

    s_repo = sanitize(repo)
    success_count = 0
    failure_count = 0
    cancelled_count = 0

    run_metrics = []
    latest_run = runs[0]

    for r in runs:
        num = r.get("run_number")
        name = sanitize(r.get("name", "Content Pipeline"))
        event = sanitize(r.get("event", "unknown"))
        conclusion = str(r.get("conclusion") or r.get("status") or "unknown").lower()

        if conclusion == "success":
            success_count += 1
            status_val = 1
        elif conclusion == "failure":
            failure_count += 1
            status_val = 0
        elif conclusion == "cancelled":
            cancelled_count += 1
            status_val = 0
        else:
            status_val = 0

        # Duration berechnen
        try:
            t_start = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            t_end = datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
            duration_s = max(0.0, (t_end - t_start).total_seconds())
            start_ts = int(t_start.timestamp())
        except Exception:
            duration_s = 0.0
            start_ts = 0

        # Detaillierte Metrik pro Run
        run_metrics.append(
            f'github_workflow_run_duration_seconds{{workflow="{name}",repo="{s_repo}",run_number="{num}",conclusion="{conclusion}",event="{event}"}} {duration_s:.1f}'
        )
        run_metrics.append(
            f'github_workflow_run_status{{workflow="{name}",repo="{s_repo}",run_number="{num}",conclusion="{conclusion}",event="{event}"}} {status_val}'
        )
        if start_ts > 0:
            run_metrics.append(
                f'github_workflow_run_timestamp_seconds{{workflow="{name}",repo="{s_repo}",run_number="{num}",conclusion="{conclusion}"}} {start_ts}'
            )

    # Berechne Erfolgsquote
    completed_evaluated = success_count + failure_count
    success_rate = (success_count / completed_evaluated * 100.0) if completed_evaluated > 0 else 100.0

    # Daten des allerneuesten Runs
    latest_name = sanitize(latest_run.get("name", "Content Pipeline"))
    latest_status = str(latest_run.get("conclusion") or latest_run.get("status") or "unknown").lower()
    latest_status_val = 1 if latest_status == "success" else 0
    latest_num = latest_run.get("run_number", 0)

    try:
        l_start = datetime.fromisoformat(latest_run["created_at"].replace("Z", "+00:00"))
        l_end = datetime.fromisoformat(latest_run["updated_at"].replace("Z", "+00:00"))
        latest_dur = max(0.0, (l_end - l_start).total_seconds())
    except Exception:
        latest_dur = 0.0

    lines = [
        "# HELP github_workflow_duration_seconds Duration of latest workflow run in seconds",
        "# TYPE github_workflow_duration_seconds gauge",
        f'github_workflow_duration_seconds{{workflow="{latest_name}",repo="{s_repo}",status="{latest_status}"}} {latest_dur:.2f}',
        "",
        "# HELP github_workflow_status Status of latest workflow run (1 for success, 0 for other)",
        "# TYPE github_workflow_status gauge",
        f'github_workflow_status{{workflow="{latest_name}",repo="{s_repo}",status="{latest_status}"}} {latest_status_val}',
        "",
        "# HELP github_workflow_latest_run_number Run-Nummer des letzten Workflow-Laufs",
        "# TYPE github_workflow_latest_run_number gauge",
        f'github_workflow_latest_run_number{{workflow="{latest_name}",repo="{s_repo}"}} {latest_num}',
        "",
        "# HELP github_workflow_runs_total Gesamtzahl der Workflow-Durchläufe nach Ergebnis",
        "# TYPE github_workflow_runs_total gauge",
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="success"}} {success_count}',
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="failure"}} {failure_count}',
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="cancelled"}} {cancelled_count}',
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="total"}} {total_count}',
        "",
        "# HELP github_workflow_success_rate_percent Erfolgsquote aller ausgewerteten Durchläufe in Prozent",
        "# TYPE github_workflow_success_rate_percent gauge",
        f'github_workflow_success_rate_percent{{repo="{s_repo}"}} {success_rate:.1f}',
        "",
        "# HELP github_workflow_run_duration_seconds Dauer jedes einzelnen Workflow-Runs in Sekunden",
        "# TYPE github_workflow_run_duration_seconds gauge",
    ]
    lines.extend(run_metrics)
    lines.append("")
    return lines


def calculate_metrics_payload(repo: str = "vananhnt994/theodor-family-content-creator") -> str:
    # 1. Read history files
    shorts_count = 0
    long_count = 0

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shorts_file = os.path.join(base_dir, "output", "historie_shorts.json")
    if os.path.exists(shorts_file):
        try:
            with open(shorts_file, "r", encoding="utf-8") as f:
                shorts_count = len(json.load(f))
        except Exception:
            pass

    long_file = os.path.join(base_dir, "output", "historie_long.json")
    if os.path.exists(long_file):
        try:
            with open(long_file, "r", encoding="utf-8") as f:
                long_count = len(json.load(f))
        except Exception:
            pass

    total_videos = shorts_count + long_count

    # Cost per video type
    cost_short_gemini = 0.005  # Trend scout + Creator + Art director
    cost_short_imagen = 0.035  # 1 image via Vertex AI Imagen
    cost_short_audio = 0.150   # ~500 characters via ElevenLabs
    cost_per_short = cost_short_gemini + cost_short_imagen + cost_short_audio  # ~$0.19

    cost_long_gemini = 0.015   # Librarian + Text cleaner + Story critic
    cost_long_imagen = 0.070   # Cover + scene images
    cost_long_audio = 2.100    # ~7000 characters via ElevenLabs
    cost_per_long = cost_long_gemini + cost_long_imagen + cost_long_audio  # ~$2.185

    # Historical cumulative cost
    total_spend_gemini = (shorts_count * cost_short_gemini) + (long_count * cost_long_gemini)
    total_spend_imagen = (shorts_count * cost_short_imagen) + (long_count * cost_long_imagen)
    total_spend_audio = (shorts_count * cost_short_audio) + (long_count * cost_long_audio)
    total_spend_apis = total_spend_gemini + total_spend_imagen + total_spend_audio

    lines = []
    # Dynamische GitHub Actions Metriken hinzufügen
    lines.extend(fetch_github_actions_metrics(repo=repo, limit=50))

    # FinOps & Production Metriken hinzufügen
    lines.extend([
        "# HELP project_total_videos_created Gesamtanzahl der erstellten Videos",
        "# TYPE project_total_videos_created gauge",
        f'project_total_videos_created{{type="shorts"}} {shorts_count}',
        f'project_total_videos_created{{type="long"}} {long_count}',
        f'project_total_videos_created{{type="total"}} {total_videos}',
        "",
        "# HELP gcp_vm_cost_dollars Kosten der Google Cloud VM in Dollar",
        "# TYPE gcp_vm_cost_dollars gauge",
        f'gcp_vm_cost_dollars{{instance="monitoring-vm",type="e2-small",period="hourly"}} {GCP_VM_HOURLY:.4f}',
        f'gcp_vm_cost_dollars{{instance="monitoring-vm",type="e2-small",period="daily"}} {GCP_VM_DAILY:.2f}',
        f'gcp_vm_cost_dollars{{instance="monitoring-vm",type="e2-small",period="monthly"}} {GCP_VM_MONTHLY:.2f}',
        "",
        "# HELP microservice_cost_per_short_dollars Kosten pro Service fuer ein Short in Dollar",
        "# TYPE microservice_cost_per_short_dollars gauge",
        'microservice_cost_per_short_dollars{service="0_trend_scout",provider="Google Gemini API"} 0.001',
        'microservice_cost_per_short_dollars{service="1_creator",provider="Google Gemini API"} 0.002',
        'microservice_cost_per_short_dollars{service="2_art_director",provider="Google Gemini API"} 0.002',
        f'microservice_cost_per_short_dollars{{service="3A_image_generator",provider="Google Vertex AI Imagen"}} {cost_short_imagen:.3f}',
        f'microservice_cost_per_short_dollars{{service="3B_audio_generator",provider="ElevenLabs TTS"}} {cost_short_audio:.3f}',
        'microservice_cost_per_short_dollars{service="4_archiver",provider="Google Drive API"} 0.000',
        'microservice_cost_per_short_dollars{service="6_video_editor",provider="Local FFmpeg"} 0.000',
        "",
        "# HELP microservice_cost_per_long_dollars Kosten pro Service fuer ein Long-Video in Dollar",
        "# TYPE microservice_cost_per_long_dollars gauge",
        'microservice_cost_per_long_dollars{service="0_librarian",provider="Google Gemini API"} 0.003',
        'microservice_cost_per_long_dollars{service="1_text_cleaner",provider="Google Gemini API"} 0.005',
        'microservice_cost_per_long_dollars{service="2_story_critic",provider="Google Gemini API"} 0.007',
        f'microservice_cost_per_long_dollars{{service="3A_cover_image",provider="Google Vertex AI Imagen"}} {cost_long_imagen:.3f}',
        f'microservice_cost_per_long_dollars{{service="3B_audio_generator",provider="ElevenLabs TTS"}} {cost_long_audio:.3f}',
        'microservice_cost_per_long_dollars{service="4_archiver",provider="Google Drive API"} 0.000',
        'microservice_cost_per_long_dollars{service="6_video_editor",provider="Local FFmpeg"} 0.000',
        "",
        "# HELP unit_economics_video_cost_dollars Stueckkosten pro Video-Einheit in Dollar",
        "# TYPE unit_economics_video_cost_dollars gauge",
        f'unit_economics_video_cost_dollars{{type="Shorts (60s)"}} {cost_per_short:.3f}',
        f'unit_economics_video_cost_dollars{{type="Long-Form (Gute Nacht)"}} {cost_per_long:.3f}',
        "",
        "# HELP cumulative_api_spend_dollars Bisher aufgelaufene API-Kosten aller produzierten Videos in Dollar",
        "# TYPE cumulative_api_spend_dollars gauge",
        f'cumulative_api_spend_dollars{{category="Google Gemini LLMs"}} {total_spend_gemini:.2f}',
        f'cumulative_api_spend_dollars{{category="Google Vertex AI Imagen"}} {total_spend_imagen:.2f}',
        f'cumulative_api_spend_dollars{{category="ElevenLabs Voice TTS"}} {total_spend_audio:.2f}',
        f'cumulative_api_spend_dollars{{category="Total Production Spend"}} {total_spend_apis:.2f}',
        "",
        "# HELP microservice_execution_seconds_average Typische Ausfuehrungsdauer pro Microservice in Sekunden",
        "# TYPE microservice_execution_seconds_average gauge",
        'microservice_execution_seconds_average{service="0_trend_scout"} 18.5',
        'microservice_execution_seconds_average{service="1_creator"} 24.2',
        'microservice_execution_seconds_average{service="2_art_director"} 15.8',
        'microservice_execution_seconds_average{service="3A_image_generator"} 38.4',
        'microservice_execution_seconds_average{service="3B_audio_generator"} 45.1',
        'microservice_execution_seconds_average{service="4_archiver"} 12.0',
        'microservice_execution_seconds_average{service="6_video_editor"} 55.0',
        "",
    ])
    return "\n".join(lines)


def push_metrics(pushgateway_url: str = None, repo: str = "vananhnt994/theodor-family-content-creator") -> bool:
    if not pushgateway_url:
        pushgateway_url = os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091")

    payload = calculate_metrics_payload(repo=repo).encode("utf-8")
    parsed = urllib.parse.urlsplit(pushgateway_url.strip())
    base_netloc = parsed.hostname + (f":{parsed.port}" if parsed.port else "")
    target_url = f"{parsed.scheme}://{base_netloc}/metrics/job/github_actions"

    req = urllib.request.Request(target_url, data=payload, method="POST")
    req.add_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")

    if parsed.username and parsed.password:
        creds = base64.b64encode(f"{parsed.username}:{parsed.password}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {creds}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"✅ Dynamic GitHub Actions & FinOps metrics pushed to {parsed.scheme}://{base_netloc} (HTTP {resp.status})!")
            return True
    except Exception as e:
        print(f"❌ Failed to push metrics: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Aggregiert Projektstatistiken, FinOps & echte GitHub Actions Runs dynamisch an Pushgateway."
    )
    parser.add_argument(
        "--pushgateway-url",
        default=os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091"),
        help="URL des Pushgateways inkl. optionalem Basic Auth (Standard: $PUSHGATEWAY_URL oder http://localhost:9091)",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("REPOSITORY", "vananhnt994/theodor-family-content-creator"),
        help="GitHub Repository Name (owner/repo)",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="Wiederhole Push alle N Sekunden (0 = einmaliger Durchlauf)",
    )
    args = parser.parse_args()

    if args.loop > 0:
        print(f"🔄 Starte dynamische Synchronisations-Schleife (Intervall: {args.loop}s)...")
        while True:
            push_metrics(pushgateway_url=args.pushgateway_url, repo=args.repo)
            time.sleep(args.loop)
    else:
        push_metrics(pushgateway_url=args.pushgateway_url, repo=args.repo)


if __name__ == "__main__":
    main()
