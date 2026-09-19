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
