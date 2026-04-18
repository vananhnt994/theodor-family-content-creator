import os
import io
import json
import logging
import sys
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Uploader")

# Scopes anpassen (Drive + YouTube Upload)
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload"
]

# Hinweis: Die Ordner-IDs werden nun dynamisch in der main() geladen

def get_oauth_credentials():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secret.json'):
                logger.error("Bitte lade die OAuth Client ID als 'client_secret.json' herunter!")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_drive_service(creds):
    return build("drive", "v3", credentials=creds)

def find_video_in_folder(drive_service, folder_id):
    query = f"'{folder_id}' in parents and mimeType='video/mp4' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name, parents)").execute()
    return results.get('files', [])

def find_seo_file(drive_service, base_name, seo_folder_id):
    seo_name = f"{base_name}_SEO.json"
    query = f"name='{seo_name}' and '{seo_folder_id}' in parents and trashed=false"
        
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if files:
        return files[0]
    return None

def download_file_in_memory(drive_service, file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return fh.getvalue()

def move_file_in_drive(drive_service, file_id, previous_parents, new_parent):
    # Füge den neuen Parent hinzu und entferne die alten
    drive_service.files().update(
        fileId=file_id,
        addParents=new_parent,
        removeParents=",".join(previous_parents),
        fields="id, parents"
    ).execute()

# --- Multiplex Upload Stubs ---

def upload_youtube(video_id, seo_data):
    # TODO: Echter Upload mit youtube API client
    logger.info("   -> [YouTube] Dummy-Upload wird ausgeführt...")
    logger.info(f"      Titel: {seo_data.get('title')}")
    # Return True on success
    return True

def upload_meta(video_id, seo_data):
    # TODO: Echter Upload via Graph API
    logger.info("   -> [Meta/IG] Upload steht auf Standby (API Keys fehlen).")
    return True

def upload_tiktok(video_id, seo_data):
    # TODO: Echter Upload via TikTok Direct Post
    logger.info("   -> [TikTok] Upload steht auf Standby (API Keys fehlen).")
    return True

def main():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    load_dotenv()

    logger.info("==================================================")
    logger.info("   🚀 Theodorbot - Service 5: The Uploader        ")
    logger.info("==================================================")

    creds = get_oauth_credentials()
    drive_service = get_drive_service(creds)

    # Kanal-Konfiguration laden
    channel_cfg = load_channel_config()
    drive_folders = channel_cfg.get("drive_folders", {})
    ready_to_post_folder = drive_folders.get("ready_to_post")
    archive_folder = drive_folders.get("uploaded_archiv")
    seos_folder = drive_folders.get("seos")
    
    if not all([ready_to_post_folder, archive_folder, seos_folder]):
        logger.error("✗ Mindestens ein Drive-Ordner (ready_to_post, uploaded_archiv, seos) fehlt in der Config.")
        sys.exit(1)

    logger.info("Schritt 1: Ordner-Scan (Ready to Post)")
    videos = find_video_in_folder(drive_service, ready_to_post_folder)
    
    if not videos:
        logger.info("Keine neuen Videos gefunden. Uploader beendet sich.")
        sys.exit(0)

    for video in videos:
        video_id = video['id']
        video_name = video['name']
        previous_parents = video.get('parents', [])
        
        logger.info(f"\n🎥 Neues Video entdeckt: {video_name}")
        
        # Basis-Name für die Dateisuche (entfernt '.mp4')
        base_name = os.path.splitext(video_name)[0]
        
        logger.info("Schritt 2: Daten-Extraktor (aus SEOs Ordner)")
        seo_file = find_seo_file(drive_service, base_name, seos_folder)
        if not seo_file:
            logger.warning(f"⚠ ACHTUNG: Keine {base_name}_SEO.json im SEOs Ordner gefunden! Überspringe dieses Video.")
            continue
            
        logger.info(f"✓ SEO-Datei gefunden: {seo_file['name']}")
        
        # Download und Parse JSON
        logger.info("   -> Lade SEO herunter...")
        raw_json = download_file_in_memory(drive_service, seo_file['id'])
        try:
            seo_data = json.loads(raw_json.decode('utf-8'))
        except Exception as e:
            logger.error(f"✗ Konnte SEO-Daten nicht parsen: {e}")
            continue
            
        if not seo_data:
            logger.warning("⚠ ACHTUNG: Keine 'seo' Daten in der Datei gefunden!")
            continue
        
        logger.info("Schritt 3: Multiplex-Upload start...")
        
        # YouTube
        success_yt = upload_youtube(video_id, seo_data)
        # Meta
        success_meta = upload_meta(video_id, seo_data)
        # TikTok
        success_tiktok = upload_tiktok(video_id, seo_data)
        
        if success_yt and success_meta and success_tiktok:
            logger.info("Schritt 4: Erfolgs-Prüfung abgeschlossen (Status 200).")
            logger.info("Schritt 5: Das Aufräumen (Move-Befehl)")
            
            try:
                move_file_in_drive(drive_service, video_id, previous_parents, archive_folder)
                logger.info(f"✓ Video verschoben nach uploaded_archiv!")
            except Exception as e:
                logger.error(f"✗ Fehler beim Verschieben: {e}")
        else:
            logger.error("✗ Mindestens ein Upload ist fehlgeschlagen. Video bleibt im ready_to_post Ordner.")
            
    logger.info("\nService 5 durchgelaufen.")

if __name__ == "__main__":
    main()
