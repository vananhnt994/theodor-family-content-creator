# 🎬 Theodorbot: The Local Video Content Factory

Eine vollautomatisierte, ressourcenschonende Microservice-Pipeline zur Erstellung von Kurzvideos (60s TikToks/Shorts) sowie Long-Form Audios (bis 12min Gute-Nacht-Geschichten). 
Optimiert für Edge-Geräte mit begrenztem Arbeitsspeicher (z.B. 8 GB RAM), da alle Services strikt nacheinander ausgeführt werden.

## 🚀 Schnellstart

```bash
# Normale Pipeline (Trend-Scout sucht automatisch ein Thema)
python run_pipeline.py --channel betheo

# Eigener Artikel-Modus (kein Scraping, eigener Text)
python run_pipeline.py --channel betheo --artikel

# Long-Form Pipeline (Gute Nacht Geschichten, liest PDF)
python run_long_pipeline.py --channel betheo

# Upload-Pipeline (fertiges Video hochladen)
python run_uploader.py --channel betheo
```

### ⏰ Automatisierte Ausführung (GitHub Actions)

Die Pipelines laufen vollautomatisch zu folgenden Zeiten:
- **Shorts-Pipeline (`run-pipeline.yml`)**: Jeden **Dienstag, Donnerstag und Sonntag um 08:00 Uhr** deutscher Zeit (06:00 UTC).
- **Video-Uploader (`run-uploader.yml`)**: Jeden **Montag, Mittwoch und Freitag um 14:00 Uhr** deutscher Zeit (12:00 UTC).


### 📝 Eigener Artikel-Modus

Statt den Trend-Scout nach Themen suchen zu lassen, kannst du deinen eigenen Artikel schreiben:

1. Öffne `input/artikel.txt`
2. Schreibe deinen Text im Format:
   ```
   TITEL: Dein Titel hier
   ---
   Dein Artikeltext hier. Der gesamte Text wird durch
   Gemini verarbeitet und als Grundlage für das Video verwendet.
   ```
3. Starte die Pipeline mit: `python run_pipeline.py --artikel`

Der Text wird trotzdem durch Gemini aufbereitet (title/description/solution), aber es wird kein Thema aus dem Internet gesucht.

---

## ⚙️ Detaillierte Service-Funktionen & Verbindungen (Short-Form Pipeline)

Die Pipeline ist als strikte Kette (Daisy-Chain) aufgebaut. Kein Service greift auf die Ressourcen des anderen zu. Die Kommunikation erfolgt ausschließlich über den Austausch von JSON-Dateien.

### 🔍 Service 0: Der Trend-Scout
Dieser Service ist der strategische Kopf der Pipeline. Er verbindet sich mit dem Internet, um Echtzeit-Daten zu sammeln, verarbeitet diese aber extrem ressourcenschonend.

* **Features:**
  * **Headless Web-Scraping:** Nutzt Playwright, um unsichtbar Foren und Nachrichtenseiten (z.B. `webtretho.vn`, `dantri.com.vn`, `vnexpress.net`, `lamchame.com`, `bbc.com/health`, `kinderzeit.de`, `1-2-family.de`) für reines Text-Scraping zu lesen.
  * **KI-Kuratierung:** Sendet die Rohdaten an Gemini Flash Lite, um das viralste und positivste Thema für die Zielgruppe zu identifizieren.
  * **Eigener Artikel-Modus:** Alternativ kann ein eigener Artikel aus `input/artikel.txt` gelesen werden (`--artikel` Flag).
  * **Duplikaterkennung:** URL-basierte Historie verhindert doppelte Themen.
* **Verbindungen:**
  * **Input:** Ziel-URLs aus `channels/<channel>.json` oder `input/artikel.txt`
  * **Output:** Generiert die Datei `output/thema.json` (enthält `title`, `description`, `solution`)

### ✍️ Service 1: The Creator (Die Redaktion)
Der kreative Motor des Systems. Entwickelt emotionale 60-Sekunden-Drehbücher mit warmem Storytelling.

* **Features:**
  * **Kontextabhängiges Storytelling:** Schreibt warme Voiceover-Drehbücher mit klarer Struktur: Emotionaler Hook → Persönliche Situation → Wendepunkt → Warme Botschaft.
  * **Szenen-Splitting:** Teilt den Text logisch in 4-6 Szenen zu je 5-8 Sekunden auf.
  * **Prompt-Drafting:** Übersetzt die Handlung jeder Szene in erste englische Bild-Prompts mit Fokus auf Character Consistency.
* **Verbindungen:**
  * **Input:** Liest `output/thema.json` aus Service 0
  * **Output:** Generiert die Datei `output/roh_skript.json`

### 🧐 Service 2: The Art Director (Die Qualitätskontrolle)
Der Wächter über den visuellen Stil. Erzwingt einen konsistenten, ruhigen Studio-Ghibli-Anime-Look.

* **Features:**
  * **Ghibli 2D Stil:** Alle Prompts werden in flat 2D Japanese anime illustration (Studio Ghibli) umgeschrieben.
  * **Simple Hintergründe:** Hintergründe sind bewusst minimal – sanfte Pastellfarben, Farbverläufe, weiche Natur-Silhouetten. Keine überladenen Szenen.
  * **Entspannte Stimmung:** Jede Szene muss Ruhe, Frieden und Gelassenheit ausstrahlen. Warme Sonnenuntergangs-Töne, weiches goldenes Licht.
  * **Character Consistency:** Volle Beschreibung (Rolle, Alter, Kleidung, Aussehen) wird in JEDEM Prompt wiederholt.
  * **Video-Prompts:** Zusätzlich zu den Bild-Prompts wird ein `video_prompt` pro Szene generiert – sanfte Kamerabewegungen und minimale Animationen.
  * **Stimmenwahl:** Analysiert das Skript und wählt die passende Sprecherstimme.
* **Verbindungen:**
  * **Input:** Liest `output/roh_skript.json` aus Service 1
  * **Output:** Generiert die Datei `output/finale_prompts.json` (mit `bild_prompt` und `video_prompt` pro Szene)

### 🖼️ Service 3A: Der Bild-Beschaffer (Cloud API Integration)
Der Übergang vom lokalen Denken zur Cloud-Power für hochauflösende Grafiken.

* **Features:**
  * **Google Vertex AI:** Nutzt Imagen 4 Fast (`imagen-4.0-fast-generate-001`) für schnelle, hochwertige Bildgenerierung im Format 9:16 (TikTok/Shorts).
  * **Automatisches Überspringen:** Bereits existierende Bilder werden nicht neu generiert.
* **Verbindungen:**
  * **Input:** Liest `output/finale_prompts.json` (spezifisch `bild_prompt` pro Szene)
  * **Output:** Speichert durchnummerierte Bilddateien (`Szene_01.jpg`, etc.) im Output-Ordner

### 🎙️ Service 3B: Der Ton-Meister (Text-to-Speech)
Erzeugt natürlich klingende Sprecherstimmen.

> [!NOTE]
> **Aktueller Status für Shorts:** Dieser Service ist für die Short-Form-Pipeline (Shorts) in `run_pipeline.py` derzeit standardmäßig deaktiviert, um Audio extern oder manuell zu verarbeiten. Er kann bei Bedarf in `run_pipeline.py` durch Einkommentieren wieder aktiviert werden. Für die Long-Form-Pipeline (`run_long_pipeline.py`) ist er weiterhin voll aktiv.

* **Features:**
  * **ElevenLabs Integration:** Nutzt das ElevenLabs Eleven v3 Modell für natürliche vietnamesische Stimmen.
  * **Stimmen (konfigurierbar in `channels/<channel>.json`):**
    * **Mann:** Deep, Resonant and Comforting
    * **Frau:** Calm and Smooth
    * **Kind:** Gentle and Playful
  * **Automatische Stimmenwahl:** Die in Service 2 gewählte Stimme wird automatisch verwendet.
* **Verbindungen:**
  * **Input:** Liest `output/finale_prompts.json` (spezifisch `voiceover_text` pro Szene)
  * **Output:** Speichert nummerierte Audiodateien im Output-Ordner

### ☁️ Service 4: Der Archiver (Cloud-Upload & Cleanup)
Der Schritt, der die Brücke zwischen dem lokalen Edge-Gerät und dem Cloud-Arbeitsplatz schlägt.

* **Features:**
  * **Markdown-Export (Storyboard):** Erstellt automatisch eine übersichtliche `Storyboard.md` mit Titel, Beschreibung, Sprechertext, Bild-Prompts und Video-Prompts.
  * **Intelligentes Zipping:** Packt alle generierten Assets (`.jpg` Bilder, `.wav` Audios, `.json` Skripte) in eine kompakte `.zip` Datei.
  * **Drive-Automatisierung:** Nutzt die Google Drive API (via OAuth 2.0), um einen neuen Projektordner zu erstellen und alle Assets hochzuladen.
* **Verbindungen:**
  * **Input:** Alle finalen Dateien aus dem lokalen `output/` Ordner
  * **Output:** Ein strukturierter Ordner in Google Drive, bereit für den Import in Adobe Premiere oder Google Labs Flow

### 🚀 Service 5: The Uploader (Multi-Plattform-Upload)
Der finale Verteilungsschritt – veröffentlicht fertige Videos auf allen Plattformen.

* **Features:**
  * **Drive-Scan:** Scannt den `ready_to_post` Google Drive-Ordner nach neuen `.mp4` Videos.
  * **SEO-Daten:** Lädt automatisch die passende `*_SEO.json` Datei mit Titel, Beschreibung und Hashtags.
  * **Multiplex-Upload:** Unterstützt parallelen Upload auf YouTube, Meta/Instagram und TikTok (API-Integration vorbereitet).
  * **Automatische Archivierung:** Nach erfolgreichem Upload wird das Video in den `uploaded_archiv` Ordner verschoben.
* **Verbindungen:**
  * **Input:** Fertige `.mp4` Videos und `*_SEO.json` Dateien aus Google Drive
  * **Output:** Veröffentlichtes Video auf YouTube/TikTok/Instagram + Archivierung
* **Ausführung:** `python run_uploader.py --channel betheo`

---

## 📚 Detaillierte Service-Funktionen (Long-Form Pipeline)

Neben der Short-Form-Pipeline existiert eine dedizierte Pipeline für längere Inhalte (bis zu 12 Minuten), die speziell für Vorlesegeschichten aus PDFs (z.B. Märchen) entwickelt wurde. Die Ausführung erfolgt über `run_long_pipeline.py`.

### 📖 Service 0: Der Librarian (in trend_scout)
Liest chronologisch Kapitel aus PDF-Büchern im Ordner `input/long/books/`. Merkt sich den Fortschritt, um beim nächsten Durchlauf das darauffolgende Kapitel zu lesen.

### 🧹 Service 1: Der Text-Cleaner (in creator)
Entfernt unerwünschte Artefakte (Seitenzahlen, Header, Inhaltsverzeichnisse) aus den rohen PDF-Texten und bereinigt den Lesefluss.

### 🖋️ Service 2: Der Story-Kritiker (in art_director)
Optimiert den Text mit LLM-Unterstützung für das Vorlesen. Wählt dynamisch eine passende Sprecherstimme.

### 🎙️ Service 3B: Ton-Meister (in audio_generator)
Teilt den sehr langen Text in kleinere Chunks auf (Chunking), verlangsamt die Sprechgeschwindigkeit (für eine ruhige "Gute-Nacht"-Stimmung) und fügt die Audio-Schnipsel per ElevenLabs zusammen.

### 🖼️ Service 3A: Cover-Bild (in image_generator) [Inaktiv]
Generiert ein passendes Cover-Bild im Ghibli-Stil für das Hörspiel. 

### 🎬 Service 6: Der Video-Editor (in video_editor) [Inaktiv]
Verbindet das Cover-Bild (Service 3A) und die Audiodatei (Service 3B) mittels FFmpeg zu einem fertigen Video mit sanftem Zoom-Effekt (Ken Burns).

> [!NOTE]
> **Aktueller Status für Long-Form:** Standardmäßig sind Service 3A (Cover-Bild) und Service 6 (Video-Editor) in `run_long_pipeline.py` deaktiviert, da das Hauptprodukt für Hörspiele eine reine Audiodatei und der zugehörige Text sind. Sie sind jedoch voll implementiert und können im Pipeline-Skript bei Bedarf durch einfaches Einkommentieren in der `services`-Liste aktiviert werden.

---

## 🛠️ Verwendeter Tech-Stack

* **Python 3.10+**: Die Kern-Logik für alle Microservices.
* **Playwright**: Für performantes Headless-Web-Scraping (Service 0).
* **Google Gemini Flash Lite**: Cloud-LLM für Themenfindung, Skripterstellung und Prompt-Verfeinerung (Services 0, 1, 2).
* **Google Vertex AI (Imagen 4 Fast)**: Hochwertige Bildgenerierung im Ghibli 2D-Stil (Service 3A).
* **ElevenLabs (Eleven v3)**: Natürliche Text-to-Speech Engine für vietnamesische Voiceovers (Service 3B).
* **Google Drive API**: Cloud-Upload und Archivierung (Services 4, 5).
* **Google OAuth 2.0**: Sichere Authentifizierung für Drive-Zugriff.
* **FFmpeg**: Für lokales Video-Rendering und Ken Burns Effekte (Service 6 - aktuell deaktiviert).

---

## 🏗️ System-Architektur

Die Pipeline nutzt Google Gemini als Cloud-LLM für intelligente Textverarbeitung und Google Vertex AI für die Bildgenerierung. ElevenLabs liefert natürliche Stimmen. Am Ende steht der manuelle Feinschliff in Adobe Premiere oder Google Labs Flow.

```text
=============================================================================
                              START (Automatischer Auslöser)
        Shorts: Di, Do, So um 08:00 Uhr (GitHub Actions: run-pipeline.yml)
        Uploader: Mo, Mi, Fr um 14:00 Uhr (GitHub Actions: run-uploader.yml)
                    ODER: python run_pipeline.py --artikel
=============================================================================
                                      │
                                      ▼
    ┌───────────────────────────────────────────────────────────────────────────┐
    │ SERVICE 0: DER TREND-SCOUT (Themenfindung)                                │
    │ Technologie: Python + Playwright + Gemini Flash Lite                      │
    │                                                                           │
    │ Funktion: 1. Liest Schlagzeilen (Webtretho, VnExpress, BBC, etc.).        │
    │           2. Gemini wählt das beste, viralste Thema aus.                  │
    │           3. Scrapt den Artikel und generiert Video-Ideen.                │
    │ ALTERNATIV: Liest eigenen Text aus input/artikel.txt (--artikel)           │
    │ Output: 'thema.json' (Titel, Beschreibung, Lösung)                       │
    └───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ (Gibt Thema an Service 1)
    ┌───────────────────────────────────────────────────────────────────────────┐
    │ SERVICE 1: THE CREATOR (Redaktion & 60s-Drehbuch)                         │
    │ Technologie: Python + Gemini Flash Lite                                   │
    │                                                                           │
    │ Funktion: Liest 'thema.json'. Schreibt ein warmes 60-Sekunden-Drehbuch.   │
    │           Zerteilt es in 4-6 Szenen à 5-8 Sekunden.                      │
    │           Erstellt erste englische Bild-Prompts mit Character Consistency. │
    │ Output: 'roh_skript.json'                                                │
    └───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ (Gibt roh_skript.json an Service 2)
    ┌────────────────────────�    ┌───────────────────────────────────┐   ┌───────────────────────────────────┐
    │ SERVICE 3A: DER BILD-BESCHAFFER   │   │ SERVICE 3B: DER TON-MEISTER       │
    │ Technologie: Python + Vertex AI   │   │ (DEAKTIVIERT FÜR SHORTS)          │
    │ (Imagen 4 Fast)                   │   │ Technologie: Python + ElevenLabs  │
    │                                   │   │ (Eleven v3)                       │
    │ Funktion: Sendet Ghibli-Prompts   │   │                                   │
    │ an Vertex AI. Lädt 9:16 Bilder.   │   │ Funktion: Wandelt Texte in        │
    │ Output: Szene_01.jpg, etc.        │   │ natürliche vietnamesische         │
    │                                   │   │ Sprecherstimme um.               │
    └───────────────────────────────────┘   └───────────────────────────────────┘──────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼ (Liest finale_prompts.json)                   ▼ (Liest Skript-Texte)
    ┌───────────────────────────────────┐   ┌───────────────────────────────────┐
    │ SERVICE 3A: DER BILD-BESCHAFFER   │   │ SERVICE 3B: DER TON-MEISTER       │
    │ Technologie: Python + Vertex AI   │   │ Technologie: Python + ElevenLabs  │
    │ (Imagen 4 Fast)                   │   │ (Eleven v3)                       │
    │                                   │   │                                   │
    │ Funktion: Sendet Ghibli-Prompts   │   │ Funktion: Wandelt Texte in        │
    │ an Vertex AI. Lädt 9:16 Bilder.   │   │ natürliche vietnamesische         │
    │ Output: Szene_01.jpg, etc.        │   │ Sprecherstimme um.               │
    └───────────────────────────────────┘   │ Output: Szene_01.wav, etc.        │
              │                             └───────────────────────────────────┘
              └───────────────────────┬───────────────────────┘
                                      ▼
                                  (Video & Assets bereit)
┌───────────────────────────────────────────────────────────────────────────┐
│ SERVICE 4: DER ARCHIVER (Cloud-Upload & Cleanup)                          │
│ Technologie: Python + Google Drive API (OAuth 2.0)                        │
│                                                                           │
│ Funktion: 1. Erstellt Storyboard.md (inkl. Video-Prompts).               │
│           2. Zippt alle Bilder, Audios und Skripte.                      │
│           3. Lädt alles nach Google Drive hoch.                          │
│ Output: Upload-Bestätigung & Google Drive Link                           │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ SERVICE 5: THE UPLOADER (Multi-Plattform-Verteilung)                      │
│ Technologie: Python + YouTube/Meta/TikTok APIs                            │
│                                                                           │
│ Funktion: 1. Scannt 'ready_to_post' Drive-Ordner nach .mp4 Videos.       │
│           2. Lädt SEO-Daten und veröffentlicht auf allen Plattformen.    │
│           3. Verschiebt fertige Videos ins Archiv.                       │
│ Output: Veröffentlichte Videos auf YouTube, TikTok, Instagram             │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
=============================================================================
                      VISUELLE KOMPOSITION (Der Mensch)
                Plattform: https://labs.google/flow/
=============================================================================
                                  │
                                  ▼
                    GOOGLE LABS FLOW (Web-Workspace)
          1. Öffne den hochgeladenen Drive-Ordner von Service 4.
          2. Importiere das Voiceover in die Flow-Timeline.
          3. Nutze die vorbereiteten Bild-Prompts und Video-Prompts
             aus der Storyboard.md, um in Flow direkt Bilder und 
             Videos zu generieren und zusammenzusetzen.
```

---

## 📁 Projektstruktur

```
theodor-family-content-creator/
├── channels/               # Channel-Konfigurationen
│   └── betheo.json          # BeTheo Channel Config (Quellen, Stimmen, Drive-IDs)
├── input/                  # Manueller Input
│   └── artikel.txt          # Eigener Artikel für --artikel Modus
├── trend_scout/            # Service 0: Trend-Scout
├── creator/                # Service 1: The Creator
├── art_director/           # Service 2: The Art Director
├── image_generator/        # Service 3A: Bild-Beschaffer
├── audio_generator/        # Service 3B: Ton-Meister
├── archiver/               # Service 4: Archiver
├── uploader/               # Service 5: Uploader
├── video_editor/           # Service 6: Video-Editor (FFmpeg)
├── output/                 # Generierte Dateien (temporär)
├── run_pipeline.py         # Haupt-Pipeline (Short-Form)
├── run_long_pipeline.py    # Long-Form Pipeline (Gute Nacht Geschichten)
├── run_uploader.py         # Upload-Pipeline (Service 5)
├── channel_config.py       # Channel-Config Loader
└── .env                    # API Keys (nicht im Git!)
```