#!/usr/bin/env python3
"""
Send GitHub Actions workflow run metrics to Google Cloud Monitoring.
Executed at the end of the pipeline to report status and duration.
"""

import os
import sys
import time

# Ensure stdout and stderr handle emojis and utf-8 across all operating systems
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def send_metrics() -> None:
    project_id = os.environ.get("GCP_PROJECT_ID", "").strip()
    if not project_id:
        print("⚠️ Warning: GCP_PROJECT_ID is not set. Skipping Cloud Monitoring metric export.", file=sys.stderr)
        return

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

    print("📊 Preparing Cloud Monitoring metrics export:")
    print(f"   Project:    {project_id}")
    print(f"   Workflow:   {workflow_name}")
    print(f"   Repository: {repository}")
    print(f"   Status:     {job_status} (val: {status_val})")
    print(f"   Duration:   {duration:.1f}s")

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

        # API Call für beide Metriken auf einmal
        client.create_time_series(name=project_name, time_series=[series_duration, series_status])
        print("✅ Metrics 'workflow_duration' and 'workflow_status' successfully published to Cloud Monitoring!")
    except Exception as exc:
        print(f"❌ Failed to publish metrics to Cloud Monitoring: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    send_metrics()
