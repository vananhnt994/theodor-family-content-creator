"""
Service 1: The Creator – Main Orchestrator
Reads thema.json → Generates voiceover script → Splits into scenes → Saves roh_skript.json
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

from creator.config import (
    GEMINI_MODEL,
    INPUT_DIR,
    INPUT_FILENAME,
    OUTPUT_DIR,
    OUTPUT_FILENAME,
    TARGET_DURATION_SECONDS,
)
from creator.script_writer import generate_voiceover, split_into_scenes

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _check_gemini() -> bool:
    """Verify that Gemini API Key is set."""
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    load_dotenv()
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        logger.error("[Creator] ✗ GEMINI_API_KEY in .env fehlt!")
        return False
    logger.info(f"[Creator] ✓ Gemini API verbunden (Modell: {GEMINI_MODEL})")
    return True


def run():
    """Execute the full Creator pipeline."""
    logger.info("=" * 60)
    logger.info("✍️  SERVICE 1: THE CREATOR (Die Redaktion)")
    logger.info("=" * 60)

    # ------------------------------------------------------------------
    # Step 0: Check Ollama
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("📡 Prüfe Gemini-Verbindung...")
    if not _check_gemini():
        logger.error("❌ Pipeline abgebrochen: Gemini API Key fehlt")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 1: Load thema.json from Service 0
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("📂 Lade Thema aus Service 0...")
    logger.info("-" * 40)

    input_path = os.path.join(INPUT_DIR, INPUT_FILENAME)
    if not os.path.exists(input_path):
        logger.error(f"❌ {input_path} nicht gefunden! Bitte zuerst Service 0 ausführen.")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        thema = json.load(f)

    logger.info(f"✅ Thema geladen: {thema.get('title', '???')}")
    logger.info(f"   Quelle: {thema.get('source', '???')}")

    # ------------------------------------------------------------------
    # Step 2: Generate voiceover script
    # ------------------------------------------------------------------
    logger.info("")
    logger.info(f"📝 Schritt 1: Voiceover-Skript generieren (~{TARGET_DURATION_SECONDS}s)...")
    logger.info("-" * 40)

    voiceover = generate_voiceover(thema)
    if not voiceover:
        logger.error("❌ Pipeline abgebrochen: Voiceover-Generierung fehlgeschlagen")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 3: Split into scenes with image prompts
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("🎬 Schritt 2: Szenen aufteilen + Bild-Prompts erstellen...")
    logger.info("-" * 40)

    scenes = split_into_scenes(
        voiceover_text=voiceover["voiceover_full"],
        mood=voiceover.get("mood", "warm"),
    )

    if not scenes:
        logger.error("❌ Pipeline abgebrochen: Szenen-Splitting fehlgeschlagen")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 4: Build and save roh_skript.json
    # ------------------------------------------------------------------
    logger.info("")
    logger.info("💾 Ergebnis speichern...")
    logger.info("-" * 40)

    total_duration = sum(s["duration_seconds"] for s in scenes)

    output = {
        "video_title": thema.get("title", ""),
        "mood": voiceover.get("mood", ""),
        "total_duration_seconds": total_duration,
        "scene_count": len(scenes),
        "seo": voiceover.get("seo", {}),
        "scenes": scenes,
        "source_thema": {
            "title": thema.get("title", ""),
            "description": thema.get("description", ""),
            "solution": thema.get("solution", ""),
            "source": thema.get("source", ""),
            "source_url": thema.get("source_url", ""),
        },
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Gespeichert: {output_path}")
    logger.info("")
    logger.info("=" * 60)
    logger.info("📋 ERGEBNIS")
    logger.info("=" * 60)
    logger.info(f"   Video-Titel:  {output['video_title']}")
    logger.info(f"   Stimmung:     {output['mood']}")
    logger.info(f"   Szenen:       {output['scene_count']}")
    logger.info(f"   Gesamtdauer:  ~{output['total_duration_seconds']}s")
    logger.info(f"   SEO-Hashtags: {output.get('seo', {}).get('hashtags', 'Fehlt')}")
    logger.info(f"   Generiert:    {output['generated_at']}")
    logger.info("-" * 40)
    for s in scenes:
        logger.info(
            f"   🎞 Szene {s['scene_number']:2d} │ {s['duration_seconds']}s │ "
            f"{s.get('emotion', '?'):12s} │ {s['voiceover_text'][:45]}..."
        )
    logger.info("=" * 60)
    logger.info("🎉 Service 1 erfolgreich abgeschlossen!")

    return output


if __name__ == "__main__":
    run()
