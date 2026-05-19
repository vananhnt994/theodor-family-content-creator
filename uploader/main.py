import os
import io
import json
import logging
import sys
import time
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
import requests

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("Uploader")

# Separate Scopes für Drive und YouTube
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Hinweis: Die Ordner-IDs werden nun dynamisch in der main() geladen

def get_oauth_credentials(token_file, scopes):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.exceptions import RefreshError
            try:
                creds.refresh(Request())
            except RefreshError:
                logger.warning(f"⚠ Refresh Token ungültig. Lösche '{token_file}' und starte neuen Login...")
                if os.path.exists(token_file):
                    os.remove(token_file)
                creds = None
        
        if not creds:
            if not os.path.exists('client_secret.json'):
                logger.error("Bitte lade die OAuth Client ID als 'client_secret.json' herunter!")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', scopes)
            creds = flow.run_local_server(port=0, prompt='select_account')
            with open(token_file, 'w') as token:
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

def download_video_to_disk(drive_service, file_id, file_path):
    request = drive_service.files().get_media(fileId=file_id)
    with open(file_path, 'wb') as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                logger.info(f"      Drive-Download: {int(status.progress() * 100)}%")

def move_file_in_drive(drive_service, file_id, previous_parents, new_parent):
    # Füge den neuen Parent hinzu und entferne die alten
    drive_service.files().update(
        fileId=file_id,
        addParents=new_parent,
        removeParents=",".join(previous_parents),
        fields="id, parents"
    ).execute()

# --- Multiplex Upload Stubs ---

def upload_youtube(video_path, seo_data):
    # Feste, unveränderbare Liste von Hashtags für BeTheo - Family
    static_hashtags = "#DayCon #NuoiDayCon #TamLyTreEm #GiaDinh"
    full_description = f"{seo_data.get('description', '')}\n\n{static_hashtags}"
    title = seo_data.get('title', 'Neues Video')
    tags_string = seo_data.get('tags', '')
    
    # Tags aufbereiten (als Liste)
    tags_list = [tag.strip() for tag in tags_string.split(',')] if tags_string else []
    
    logger.info("   -> [YouTube] Starte Upload-Prozess...")
    
    try:
        logger.info("      Video wird zu YouTube hochgeladen (Login erforderlich)...")
        # Authentifizierung genau hier auslösen
        youtube_creds = get_oauth_credentials('youtube_token.json', YOUTUBE_SCOPES)
        youtube_service = build("youtube", "v3", credentials=youtube_creds)
        
        body = {
            'snippet': {
                'title': title,
                'description': full_description,
                'tags': tags_list,
                'categoryId': "22"  # People & Blogs
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype='video/mp4')
        
        request = youtube_service.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"      YouTube-Upload: {int(status.progress() * 100)}%")
                
        logger.info(f"   ✓ [YouTube] Video erfolgreich hochgeladen! Video-ID: {response.get('id')}")
        return True
        
    except Exception as e:
        logger.error(f"   ✗ [YouTube] Fehler beim Upload: {e}")
        return False
    # Hinweis: Cleanup passiert jetzt zentral in der main() Schleife

def upload_meta(video_path, seo_data):
    static_hashtags = "#DayCon #NuoiDayCon #TamLyTreEm #GiaDinh"
    page_id = os.getenv("FACEBOOK_PAGE_ID")
    access_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    
    if not page_id or not access_token:
        logger.info(f"   -> [Meta/FB] Upload übersprungen (API Keys fehlen in .env). Hashtags: {static_hashtags}")
        return True 
        
    logger.info("   -> [Meta/FB] Starte Upload auf Facebook Page...")
    url = f"https://graph.facebook.com/v21.0/{page_id}/videos"
    
    # Beschreibung zusammenbauen
    description = f"{seo_data.get('title')}\n\n{seo_data.get('description', '')}\n\n{static_hashtags}"
    
    payload = {
        'description': description,
        'access_token': access_token
    }
    
    try:
        with open(video_path, 'rb') as f:
            files = {'source': f}
            response = requests.post(url, data=payload, files=files)
            
        if response.status_code == 200:
            result = response.json()
            logger.info(f"   ✓ [Meta/FB] Video erfolgreich hochgeladen! Facebook Video ID: {result.get('id')}")
            return True
        else:
            logger.error(f"   ✗ [Meta/FB] Fehler beim Facebook-Upload: {response.text}")
            return False
    except Exception as e:
        logger.error(f"   ✗ [Meta/FB] Ausnahme beim Facebook-Upload: {e}")
        return False

def upload_tiktok(video_path, seo_data):
    static_hashtags = "#DayCon #NuoiDayCon #TamLyTreEm #GiaDinh"
    # TODO: Echter Upload via TikTok Direct Post
    logger.info(f"   -> [TikTok] Upload steht auf Standby (API Keys fehlen). Hashtags: {static_hashtags}")
    return True

def main():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    load_dotenv()

    logger.info("==================================================")
    logger.info("   🚀 Theodorbot - Service 5: The Uploader        ")
    logger.info("==================================================")

    # Erstelle Login für Drive (wo die Videos liegen)
    logger.info("Schritt 0.1: Authentifiziere Google Drive...")
    drive_creds = get_oauth_credentials('drive_token.json', DRIVE_SCOPES)
    drive_service = get_drive_service(drive_creds)
    
    # YouTube-Login wurde in den Upload-Schritt verschoben!

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
        
        temp_file_path = f"temp_{video_id}.mp4"
        success_all = False
        
        try:
            # Video EINMAL herunterladen
            logger.info(f"   -> Lade Video für alle Plattformen herunter...")
            download_video_to_disk(drive_service, video_id, temp_file_path)
            
            # YouTube
            success_yt = upload_youtube(temp_file_path, seo_data)
            
            # Meta (Aktuell deaktiviert, da FACEBOOK_PAGE_ACCESS_TOKEN in .env noch ein Platzhalter ist)
            # logger.info("   -> [Meta/FB] Upload vorübergehend deaktiviert.")
            success_meta = True
            
            # TikTok (Aktuell deaktiviert / Standby)
            # logger.info("   -> [TikTok] Upload vorübergehend deaktiviert.")
            success_tiktok = True
            
            success_all = success_yt and success_meta and success_tiktok
            
        except Exception as e:
            logger.error(f"✗ Kritischer Fehler im Upload-Loop: {e}")
            success_all = False
        finally:
            # Räume temporäre Datei nach allen Uploads auf
            if os.path.exists(temp_file_path):
                try:
                    time.sleep(1)
                    os.remove(temp_file_path)
                except:
                    pass

        if success_all:
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
