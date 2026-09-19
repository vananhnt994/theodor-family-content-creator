#!/usr/bin/env python3
"""
export_metrics.py - Aggregates project statistics, microservice costs, and GCP VM costs,
and pushes them to Prometheus Pushgateway.
"""

import base64
import json
import os
import sys
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


def calculate_metrics_payload() -> str:
    # 1. Read history files
    shorts_count = 0
    long_count = 0

    shorts_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "historie_shorts.json")
    if os.path.exists(shorts_file):
        try:
            with open(shorts_file, "r", encoding="utf-8") as f:
                shorts_count = len(json.load(f))
        except Exception:
            pass

    long_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "historie_long.json")
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

    lines = [
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
    ]
    return "\n".join(lines)


def push_metrics(pushgateway_url: str = None) -> bool:
    if not pushgateway_url:
        pushgateway_url = os.environ.get("PUSHGATEWAY_URL", "http://admin:ih_Jk_ElStNn6IlTAotYUA@35.246.243.104:9091")

    payload = calculate_metrics_payload().encode("utf-8")
    parsed = urllib.parse.urlsplit(pushgateway_url.strip())
    base_netloc = parsed.hostname + (f":{parsed.port}" if parsed.port else "")
    target_url = f"{parsed.scheme}://{base_netloc}/metrics/job/theodor_project_finops"

    req = urllib.request.Request(target_url, data=payload, method="POST")
    req.add_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")

    if parsed.username and parsed.password:
        creds = base64.b64encode(f"{parsed.username}:{parsed.password}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {creds}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"✅ Project & FinOps metrics pushed successfully (HTTP {resp.status})!")
            return True
    except Exception as e:
        print(f"❌ Failed to push metrics: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    push_metrics()
