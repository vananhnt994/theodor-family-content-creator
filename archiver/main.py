import os
import json
import logging
import zipfile
import sys
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Archiver")

INPUT_DIR = "output"
INPUT_JSON = "output/finale_prompts.json"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def create_storyboard(data: dict) -> str:
    sb_path = os.path.join(INPUT_DIR, "Storyboard.md")
    with open(sb_path, "w", encoding="utf-8") as f:
        f.write(f"# 🎬 {data.get('video_title', 'Video Storyboard')}\n\n")
        f.write(f"**Stimme:** {data.get('selected_voice', 'Unbekannt')}\n\n")
        for scene in data.get("scenes", []):
            sn = scene.get("scene_number")
            f.write(f"## Szene {sn}\n")
            f.write(f"**Voiceover:** {scene.get('voiceover_text')}\n\n")
            f.write(f"**Bild-Prompt (Final):** {scene.get('bild_prompt')}\n\n")
            f.write("---\n")
    return sb_path

def create_zip(archive_path: str):
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(INPUT_DIR):
            for file in files:
                if file.endswith((".json", ".jpg", ".wav", ".mp3", ".md")):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, INPUT_DIR)
                    zipf.write(file_path, arcname)

def get_oauth_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secret.json'):
                raise FileNotFoundError("Bitte lade die OAuth Client ID als 'client_secret.json' in den Ordner herunter!")
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def upload_to_drive(file_path: str, filename: str, folder_id: str):
    creds = get_oauth_credentials()
    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": filename,
        "parents": [folder_id] if folder_id else []
    }
    media = MediaFileUpload(file_path, mimetype="application/zip", resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    return file

def cleanup_output_dir():
    logger.info("🧹 Bereinige output-Ordner (behalte historie.json)...")
    for root, _, files in os.walk(INPUT_DIR):
        for file in files:
            if file != "historie.json":
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"⚠ Konnte {file} nicht löschen: {e}")
    logger.info("✓ Ordner bereinigt.")

def main():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(env_path)
    load_dotenv()
    
    logger.info("==================================================")
    logger.info("   ☁️  Theodorbot - Service 4: Der Archiver       ")
    logger.info("==================================================")

    if not os.path.exists(INPUT_JSON):
        logger.error(f"✗ Datei {INPUT_JSON} nicht gefunden!")
        sys.exit(1)

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Storyboard erstellen
    sb_path = create_storyboard(data)
    logger.info(f"✓ Storyboard generiert: {sb_path}")

    # 2. ZIP erstellen
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"Projekt_{timestamp}.zip"
    zip_path = os.path.join(INPUT_DIR, zip_name)
    
    create_zip(zip_path)
    logger.info(f"✓ ZIP-Archiv gepackt: {zip_path}")

    # 3. Upload zu Google Drive
    folder_id = os.environ.get("DRIVE_FOLDER_ID")
    if not folder_id:
        logger.warning("⚠ DRIVE_FOLDER_ID fehlt in der .env. Lade ins Hauptverzeichnis hoch...")

    try:
        logger.info("☁️  Lade Archiv zu Google Drive hoch...")
        file_res = upload_to_drive(zip_path, zip_name, folder_id)
        logger.info(f"✓ Erfolgreich hochgeladen! Link: {file_res.get('webViewLink')}")
        
        # 4. Ordner aufräumen
        cleanup_output_dir()
    except Exception as e:
        logger.error(f"✗ Fehler beim Google Drive Upload: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
