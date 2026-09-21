#!/usr/bin/env python3
"""
Send GitHub Actions workflow run metrics to Google Cloud Monitoring and Prometheus Pushgateway.
Executed at the end of the pipeline to report status and duration.
"""

import base64
import os
import sys
import time
import urllib.parse
import urllib.request

# Ensure stdout and stderr handle emojis and utf-8 across all operating systems
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _get_project_and_cost_metrics() -> list:
    """Calculate and return project production counts and FinOps cost metrics."""
    import json
    shorts_count = 0
    long_count = 0

    shorts_file = "output/historie_shorts.json"
    if os.path.exists(shorts_file):
        try:
            with open(shorts_file, "r", encoding="utf-8") as f:
                shorts_count = len(json.load(f))
        except Exception:
            pass

    long_file = "output/historie_long.json"
    if os.path.exists(long_file):
        try:
            with open(long_file, "r", encoding="utf-8") as f:
                long_count = len(json.load(f))
        except Exception:
            pass

    total_videos = shorts_count + long_count

    cost_short_gemini = 0.005
    cost_short_imagen = 0.035
    cost_short_audio = 0.150
    cost_per_short = cost_short_gemini + cost_short_imagen + cost_short_audio

    cost_long_gemini = 0.015
    cost_long_imagen = 0.070
    cost_long_audio = 2.100
    cost_per_long = cost_long_gemini + cost_long_imagen + cost_long_audio

    total_spend_gemini = (shorts_count * cost_short_gemini) + (long_count * cost_long_gemini)
    total_spend_imagen = (shorts_count * cost_short_imagen) + (long_count * cost_long_imagen)
    total_spend_audio = (shorts_count * cost_short_audio) + (long_count * cost_long_audio)
    total_spend_apis = total_spend_gemini + total_spend_imagen + total_spend_audio

    gcp_vm_monthly = 15.60
    gcp_vm_daily = 0.52
    gcp_vm_hourly = 0.0208

    return [
        "# HELP project_total_videos_created Gesamtanzahl der erstellten Videos",
        "# TYPE project_total_videos_created gauge",
        f'project_total_videos_created{{type="shorts"}} {shorts_count}',
        f'project_total_videos_created{{type="long"}} {long_count}',
        f'project_total_videos_created{{type="total"}} {total_videos}',
        "",
        "# HELP gcp_vm_cost_dollars Kosten der Google Cloud VM in Dollar",
        "# TYPE gcp_vm_cost_dollars gauge",
        f'gcp_vm_cost_dollars{{instance="monitoring-vm",type="e2-small",period="hourly"}} {gcp_vm_hourly:.4f}',
        f'gcp_vm_cost_dollars{{instance="monitoring-vm",type="e2-small",period="daily"}} {gcp_vm_daily:.2f}',
        f'gcp_vm_cost_dollars{{instance="monitoring-vm",type="e2-small",period="monthly"}} {gcp_vm_monthly:.2f}',
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
    ]


def _fetch_github_runs_metrics(repository: str, limit: int = 50) -> list:
    """Ruft dynamisch die letzten Runs aus der GitHub Actions REST API ab."""
    from datetime import datetime
    import json
    url = f"https://api.github.com/repos/{repository}/actions/runs?per_page={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "Monitoring-Exporter"})
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        req.add_header("Authorization", f"Bearer {github_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    runs = data.get("workflow_runs", [])
    if not runs:
        return []

    total_count = data.get("total_count", len(runs))
    s_repo = str(repository).replace('"', '\\"')
    success_count = sum(1 for r in runs if str(r.get("conclusion") or "").lower() == "success")
    failure_count = sum(1 for r in runs if str(r.get("conclusion") or "").lower() == "failure")
    cancelled_count = sum(1 for r in runs if str(r.get("conclusion") or "").lower() == "cancelled")
    evaluated = success_count + failure_count
    success_rate = (success_count / evaluated * 100.0) if evaluated > 0 else 100.0

    lines = [
        "# HELP github_workflow_latest_run_number Run-Nummer des letzten Workflow-Laufs",
        "# TYPE github_workflow_latest_run_number gauge",
        f'github_workflow_latest_run_number{{repo="{s_repo}"}} {runs[0].get("run_number", 0)}',
        "# HELP github_workflow_runs_total Gesamtzahl der Workflow-Durchlaeufe nach Ergebnis",
        "# TYPE github_workflow_runs_total gauge",
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="success"}} {success_count}',
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="failure"}} {failure_count}',
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="cancelled"}} {cancelled_count}',
        f'github_workflow_runs_total{{repo="{s_repo}",conclusion="total"}} {total_count}',
        "# HELP github_workflow_success_rate_percent Erfolgsquote aller ausgewerteten Durchlaeufe in Prozent",
        "# TYPE github_workflow_success_rate_percent gauge",
        f'github_workflow_success_rate_percent{{repo="{s_repo}"}} {success_rate:.1f}',
        "# HELP github_workflow_run_duration_seconds Dauer jedes einzelnen Workflow-Runs in Sekunden",
        "# TYPE github_workflow_run_duration_seconds gauge",
    ]

    for r in runs:
        num = r.get("run_number")
        name = str(r.get("name", "Content Pipeline")).replace('"', '\\"')
        event = str(r.get("event", "unknown")).replace('"', '\\"')
        conc = str(r.get("conclusion") or r.get("status") or "unknown").lower()
        try:
            t_start = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            t_end = datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))
            dur = max(0.0, (t_end - t_start).total_seconds())
        except Exception:
            dur = 0.0
        lines.append(f'github_workflow_run_duration_seconds{{workflow="{name}",repo="{s_repo}",run_number="{num}",conclusion="{conc}",event="{event}"}} {dur:.1f}')

    return lines


def push_to_prometheus_pushgateway(
    pushgateway_url: str,
    workflow_name: str,
    job_status: str,
    repository: str,
    duration: float,
    status_val: int,
) -> None:
    """Push metrics to Prometheus Pushgateway using Basic Auth if provided."""
    try:
        parsed = urllib.parse.urlsplit(pushgateway_url.strip())
        base_netloc = parsed.hostname + (f":{parsed.port}" if parsed.port else "")
        target_url = f"{parsed.scheme}://{base_netloc}/metrics/job/github_actions"

        def sanitize_label(val: str) -> str:
            return val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

        s_workflow = sanitize_label(workflow_name)
        s_repo = sanitize_label(repository)
        s_status = sanitize_label(job_status)

        lines = [
            "# HELP github_workflow_duration_seconds Duration of workflow run in seconds",
            "# TYPE github_workflow_duration_seconds gauge",
            f'github_workflow_duration_seconds{{workflow="{s_workflow}",repo="{s_repo}",status="{s_status}"}} {duration:.2f}',
            "# HELP github_workflow_status Status of workflow run (1 for success, 0 for other)",
            "# TYPE github_workflow_status gauge",
            f'github_workflow_status{{workflow="{s_workflow}",repo="{s_repo}",status="{s_status}"}} {int(status_val)}',
            "",
        ]
        # Dynamische GitHub Actions Runs anhängen
        lines.extend(_fetch_github_runs_metrics(repository=repository, limit=50))
        lines.extend(_get_project_and_cost_metrics())
        payload = "\n".join(lines).encode("utf-8")

        req = urllib.request.Request(target_url, data=payload, method="POST")
        req.add_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")

        if parsed.username and parsed.password:
            user_pass = f"{parsed.username}:{parsed.password}".encode("utf-8")
            b64_auth = base64.b64encode(user_pass).decode("ascii")
            req.add_header("Authorization", f"Basic {b64_auth}")

        with urllib.request.urlopen(req, timeout=15) as resp:
            if 200 <= resp.status < 300:
                print(f"✅ Metrics successfully pushed to Prometheus Pushgateway ({target_url})!")
            else:
                print(f"⚠️ Pushgateway returned unexpected status: {resp.status}", file=sys.stderr)
    except Exception as exc:
        print(f"⚠️ Failed to push metrics to Prometheus Pushgateway: {exc}", file=sys.stderr)


def send_to_gcp_cloud_monitoring(
    project_id: str,
    workflow_name: str,
    job_status: str,
    repository: str,
    duration: float,
    status_val: int,
    now: float,
) -> None:
    """Send metrics to Google Cloud Monitoring using Google Cloud Client Library."""
    try:
        from google.cloud import monitoring_v3
        from google.protobuf.timestamp_pb2 import Timestamp

        client = monitoring_v3.MetricServiceClient()
        project_name = f"projects/{project_id}"

        seconds = int(now)
        nanos = int((now - seconds) * 10**9)
        end_time = Timestamp(seconds=seconds, nanos=nanos)
        interval = monitoring_v3.TimeInterval(end_time=end_time)

        # 1. Metrik: Laufzeit (workflow_duration)
        series_duration = monitoring_v3.TimeSeries()
        series_duration.metric.type = "custom.googleapis.com/github/workflow_duration"
        series_duration.metric.labels["workflow"] = str(workflow_name)
        series_duration.metric.labels["repo"] = str(repository)
        series_duration.resource.type = "global"
        series_duration.resource.labels["project_id"] = str(project_id)

        point_duration = monitoring_v3.Point(
            interval=interval,
            value={"double_value": float(duration)},
        )
        series_duration.points = [point_duration]

        # 2. Metrik: Erfolgsstatus (workflow_status: 1=success, 0=other)
        series_status = monitoring_v3.TimeSeries()
        series_status.metric.type = "custom.googleapis.com/github/workflow_status"
        series_status.metric.labels["workflow"] = str(workflow_name)
        series_status.metric.labels["repo"] = str(repository)
        series_status.resource.type = "global"
        series_status.resource.labels["project_id"] = str(project_id)

        point_status = monitoring_v3.Point(
            interval=interval,
            value={"int64_value": int(status_val)},
        )
        series_status.points = [point_status]

        client.create_time_series(name=project_name, time_series=[series_duration, series_status])
        print("✅ Metrics 'workflow_duration' and 'workflow_status' successfully published to Cloud Monitoring!")
    except Exception as exc:
        print(f"❌ Failed to publish metrics to Cloud Monitoring: {exc}", file=sys.stderr)
        raise


def send_metrics() -> None:
    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    pushgateway_url = os.environ.get("PUSHGATEWAY_URL", "").strip()

    workflow_name = os.environ.get("WORKFLOW_NAME", "unknown_workflow")
    job_status = os.environ.get("JOB_STATUS", "unknown")
    repository = os.environ.get("REPOSITORY", "unknown_repo")

    # Determine duration
    now = time.time()
    duration = 0.0
    duration_str = os.environ.get("DURATION", "").strip()
    start_time_str = os.environ.get("START_TIME", "").strip()

    if duration_str:
        try:
            duration = max(0.0, float(duration_str))
        except ValueError:
            pass
    elif start_time_str:
        try:
            duration = max(0.0, now - float(start_time_str))
        except ValueError:
            pass

    # Determine status value (1 for success, 0 for anything else)
    status_val_str = os.environ.get("STATUS_VAL", "").strip()
    if status_val_str:
        try:
            status_val = int(status_val_str)
        except ValueError:
            status_val = 1 if job_status.lower() == "success" else 0
    else:
        status_val = 1 if job_status.lower() == "success" else 0

    print("📊 Preparing Metrics export:")
    print(f"   Workflow:   {workflow_name}")
    print(f"   Repository: {repository}")
    print(f"   Status:     {job_status} (code: {status_val})")
    print(f"   Duration:   {duration:.1f}s")
    if pushgateway_url:
        print("   Pushgateway: Configured (via PUSHGATEWAY_URL secret)")
    if project_id:
        print(f"   GCP Project: {project_id}")

    # 1. Prometheus Pushgateway Export
    if pushgateway_url:
        push_to_prometheus_pushgateway(
            pushgateway_url=pushgateway_url,
            workflow_name=workflow_name,
            job_status=job_status,
            repository=repository,
            duration=duration,
            status_val=status_val,
        )

    # 2. Google Cloud Monitoring Export
    if project_id:
        send_to_gcp_cloud_monitoring(
            project_id=project_id,
            workflow_name=workflow_name,
            job_status=job_status,
            repository=repository,
            duration=duration,
            status_val=status_val,
            now=now,
        )
    elif not pushgateway_url:
        print("⚠️ Warning: Neither GCP_PROJECT_ID nor PUSHGATEWAY_URL is configured. No metrics exported.", file=sys.stderr)


if __name__ == "__main__":
    send_metrics()
