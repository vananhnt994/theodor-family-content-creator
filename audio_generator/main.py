import os
import json
import logging
import sys
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

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
        
    selected_voice = data.get("selected_voice", "Anh")
    voice_id_env_key = f"ELEVENLABS_VOICE_ID_{selected_voice.upper()}"
    voice_id = os.environ.get(voice_id_env_key)
    
    if not voice_id:
        logger.warning(f"⚠ Voice ID für {selected_voice} nicht in .env gefunden. Nutze Default Anh.")
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID_ANH", "ywBZEqUhld86Jeajq94o")
        
    scenes = data.get("scenes", [])
    has_error = False
    for scene in scenes:
        sn = scene.get("scene_number")
        text = scene.get("voiceover_text")
        
        if not text: continue
        
        # Speichern als mp3 anstelle von wav da ElevenLabs nativ komprimiertes mp3 liefert
        out_path = os.path.join(OUTPUT_DIR, f"Szene_{sn:02d}.mp3")
        if os.path.exists(out_path):
            logger.info(f"Szene {sn} Audio existiert bereits. Überspringe...")
            continue
            
        logger.info(f"🎙️ Generiere Voiceover für Szene {sn} mit {selected_voice}...")
        try:
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,
                output_format="mp3_44100_128",
                text=text,
                model_id="eleven_turbo_v2_5",
            )
            with open(out_path, "wb") as f_out:
                for chunk in audio_generator:
                    if chunk:
                        f_out.write(chunk)
            
            logger.info(f"✓ Audio gespeichert: {out_path}")
        except Exception as e:
            logger.error(f"✗ Fehler bei Szene {sn} Audio: {e}")
            if os.path.exists(out_path):
                os.remove(out_path)
            has_error = True

    if has_error:
        sys.exit(1)

if __name__ == "__main__":
    main()
