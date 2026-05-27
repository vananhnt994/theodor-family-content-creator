import os
import json
import logging
import sys
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("AudioGenerator")

INPUT_FILE = "output/finale_prompts.json"
OUTPUT_DIR = "output"

# ElevenLabs character limit per request (OP-7: raised from 2400 to 4500 → ~50% fewer API calls)
# ElevenLabs allows up to 5000 chars per request; 4500 gives a safe margin.
CHUNK_CHAR_LIMIT = 4500


def _split_into_chunks(text: str, limit: int = CHUNK_CHAR_LIMIT) -> list[str]:
    """
    Split text into chunks at sentence boundaries, keeping each chunk
    under `limit` characters.
    """
    import re
    # Split at sentence-ending punctuation followed by a space or newline
    sentences = re.split(r'(?<=[.!?…»])\s+', text)

    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= limit:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            # If a single sentence is too long, split it hard
            if len(sentence) > limit:
                for i in range(0, len(sentence), limit):
                    chunks.append(sentence[i:i + limit])
                current = ""
            else:
                current = sentence
    if current:
        chunks.append(current)
    return chunks


def generate_long_audio(text: str, voice_id: str, client: ElevenLabs, out_path: str, category: str = "schlaf"):
    """
    Generate audio for a long text by splitting into chunks
    and concatenating the binary audio data.
    Category controls the voice dynamics:
    - schlaf: calm, stable narration for bedtime
    - natur: slightly more energetic for nature discovery
    """
    chunks = _split_into_chunks(text)
    logger.info(f"🎙️ Long-Form Audio ({category}): {len(chunks)} Chunks ({len(text)} Zeichen gesamt)...")

    if category == "natur":
        voice_settings = VoiceSettings(
            stability=0.50,
            similarity_boost=0.80,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0  # Normal narration speed for nature exploration
        )
    else:
        voice_settings = VoiceSettings(
            stability=0.60,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0  # Calm narration speed for bedtime stories
        )

    audio_data = b""
    for i, chunk in enumerate(chunks, 1):
        logger.info(f"   Chunk {i}/{len(chunks)} ({len(chunk)} Zeichen)...")
        try:
            generator = client.text_to_speech.convert(
                voice_id=voice_id,
                output_format="mp3_44100_128",
                text=chunk,
                model_id="eleven_v3",
                voice_settings=voice_settings,
            )
            for part in generator:
                if part:
                    audio_data += part
        except Exception as e:
            logger.error(f"✗ Fehler bei Chunk {i}: {e}")
            raise

    with open(out_path, "wb") as f:
        f.write(audio_data)
    logger.info(f"✓ Long-Form Audio gespeichert: {out_path} ({len(audio_data):,} Bytes)")


def main():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    load_dotenv()

    logger.info("==================================================")
    logger.info("   🎙️ Theodorbot - Service 3B: Der Ton-Meister    ")
    logger.info("==================================================")

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        logger.error("✗ ELEVENLABS_API_KEY fehlt in .env")
        sys.exit(1)

    client = ElevenLabs(api_key=api_key)

    if not os.path.exists(INPUT_FILE):
        logger.error(f"✗ Input Datei {INPUT_FILE} fehlt.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    channel_cfg = load_channel_config()
    voice_mapping = channel_cfg.get("voices", {})

    selected_voice = data.get("selected_voice", list(voice_mapping.keys())[0] if voice_mapping else "Mann")
    voice_id = voice_mapping.get(selected_voice, "6sFKzaJr574YWVu4UuJF")

    out_path = os.path.join(OUTPUT_DIR, "Voiceover_Finale.mp3")

    # ------------------------------------------------------------------
    # Long-Form mode: chunked audio generation with calm voice settings
    # ------------------------------------------------------------------
    if data.get("mode") == "long":
        category = data.get("category", "schlaf")
        text = data.get("optimized_text", data.get("cleaned_text", ""))
        if not text:
            logger.error("✗ Kein Text ('optimized_text' oder 'cleaned_text') in finale_prompts.json gefunden.")
            sys.exit(1)

        if os.path.exists(out_path):
            logger.info(f"Audio existiert bereits ({out_path}). Überspringe Generierung...")
            return

        logger.info(f"🎙️ Long-Form ({category}): Generiere Voiceover mit Stimme '{selected_voice}' (ID: {voice_id})...")
        try:
            generate_long_audio(text, voice_id, client, out_path, category=category)
        except Exception as e:
            logger.error(f"✗ Fehler bei Long-Form Audio Generierung: {e}")
            if os.path.exists(out_path):
                os.remove(out_path)
            sys.exit(1)
        return

    # ------------------------------------------------------------------
    # Shorts mode: single combined voiceover from scenes
    # ------------------------------------------------------------------
    scenes = data.get("scenes", [])

    full_text_fragments = []
    for scene in scenes:
        text = scene.get("voiceover_text", "").strip()
        if text:
            full_text_fragments.append(text)

    if not full_text_fragments:
        logger.error("✗ Kein Voiceover-Text in den Szenen gefunden.")
        sys.exit(1)

    full_text = ' <break time="0.5s" /> '.join(full_text_fragments)

    if os.path.exists(out_path):
        logger.info(f"Audio existiert bereits ({out_path}). Überspringe Generierung...")
    else:
        logger.info(f"🎙️ Generiere gemeinsames Voiceover mit Stimme '{selected_voice}' (ID: {voice_id})...")
        try:
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,
                output_format="mp3_44100_128",
                text=full_text,
                model_id="eleven_v3",
                voice_settings=VoiceSettings(
                    stability=0.45,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True,
                    speed=1.1
                )
            )
            with open(out_path, "wb") as f_out:
                for chunk in audio_generator:
                    if chunk:
                        f_out.write(chunk)

            logger.info(f"✓ Komplettes Audio gespeichert: {out_path}")
        except Exception as e:
            logger.error(f"✗ Fehler bei der Audio Generierung: {e}")
            if os.path.exists(out_path):
                os.remove(out_path)
            sys.exit(1)


if __name__ == "__main__":
    main()
