import os
import json
import logging
import sys
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("AudioGenerator")

INPUT_FILE = "output/finale_prompts.json"
OUTPUT_DIR = "output"

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
    voice_id = voice_mapping.get(selected_voice, "6sFKzaJr574YWVu4UuJF") # Default Fallback
        
    scenes = data.get("scenes", [])
    
    # 1. Alle Texte der Szenen kombinieren
    full_text_fragments = []
    for scene in scenes:
        text = scene.get("voiceover_text", "").strip()
        if text:
            full_text_fragments.append(text)
            
    if not full_text_fragments:
        logger.error("✗ Kein Voiceover-Text in den Szenen gefunden.")
        sys.exit(1)
        
    # Texte mit sehr kurzem Abstand (0.5 Sekunden) verbinden für mehr Dynamik.
    full_text = ' <break time="0.5s" /> '.join(full_text_fragments)
    
    out_path = os.path.join(OUTPUT_DIR, "Voiceover_Finale.mp3")
    if os.path.exists(out_path):
        logger.info(f"Audio existiert bereits ({out_path}). Überspringe Generierung...")
    else:
        from elevenlabs import VoiceSettings
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
