# 🎬 Theodorbot: The Local Video Content Factory

Eine vollautomatisierte, ressourcenschonende Microservice-Pipeline zur Erstellung von Kurzvideos (TikToks, YouTube Shorts). 
Optimiert für Edge-Geräte mit begrenztem Arbeitsspeicher (z.B. 8 GB RAM), da alle Services strikt nacheinander ausgeführt werden.

## ⚙️ Detaillierte Service-Funktionen & Verbindungen

Die Pipeline ist als strikte Kette (Daisy-Chain) aufgebaut. Kein Service greift auf die Ressourcen des anderen zu. Die Kommunikation erfolgt ausschließlich über den Austausch von JSON-Dateien.

### 🔍 Service 0: Der Trend-Scout
Dieser Service ist der strategische Kopf der Pipeline. Er verbindet sich mit dem Internet, um Echtzeit-Daten zu sammeln, verarbeitet diese aber extrem ressourcenschonend.

* **Features:**
  * **Headless Web-Scraping:** Nutzt Playwright, um unsichtbar Foren (z.B.  `webtretho.com`, `dantri.com.vn`, `vnexpress.net`, `lamchame.com` für reines Text-Scraping ohne JavaScript-Overhead) zu lesen.
  * **KI-Kuratierung:** Sendet die Rohdaten an eine externe API (z.B. Gemini Flash/Pro via Free Tier), um das viralste und sinnvollste und positive Themen für die Zielgruppe der Erziehung, Familienwahnsinn und Alltag in Vietnam zu identifizieren.
* **Verbindungen:**
  * **Input:** Ziel-URLs (z.B. `webtretho.com`, `dantri.com.vn`, `vnexpress.net`, `lamchame.com`).
  * **Output:** Generiert die Datei `thema.json` (enthält `titel` und `beschreibung`).

### ✍️ Service 1: The Creator (Die Redaktion)
Der kreative Motor des Systems. Entwickelt Inhalte, die emotional fesseln und eine hohe Watch-Time garantieren, basierend auf erfolgreichen Hook-Strategien.

* **Features:**
  * **Strukturierte Skript-Erstellung:** Schreibt warme Voiceover-Drehbücher mit klaren Strukturen (z.B. Alltags-Metaphern, "3-Tipps"-Listen) für hohe Relevanz bei Eltern und Teenies.
  * **Szenen-Splitting:** Teilt den Text logisch in knackige 3- bis 5-Sekunden-Abschnitte auf. Keine langatmigen Pausen.
  * **Prompt-Drafting:** Übersetzt die Handlung jeder Szene in erste englische Bild-Prompts mit starkem Fokus auf das zentrale Motiv.
* **Verbindungen:**
  * **Input:** Liest `thema.json` aus Service 0.
  * **Output:** Generiert die Datei `roh_skript.json`.

### 🧐 Service 2: The Art Director (Die Qualitätskontrolle)
Der Wächter über den visuellen Stil. Verhindert langweilige Stockfotos und erzwingt einen aufmerksamkeitsstarken, viralen Look (Fokus auf starke Emotionen und Close-ups).

* **Features:**
  * **Mimik & Fokus-Enforcement:** Optimiert die Prompts gezielt auf ausdrucksstarke, teils übertriebene Mimik ("hyper-expressive faces") und enge Porträts ("close-up shot"), da diese in Kurzvideos am besten konvertieren.
  * **Prompt-Sanitization:** Löscht rigoros Standard-KI-Vokabular ("epic", "masterpiece") und überladene Hintergrundbeschreibungen, um das Hauptmotiv sauber zu halten.
  * **Style-Konsistenz:** Fügt feste Parameter für satte Farben und ansprechende Beleuchtung hinzu (z.B. "vibrant colors", "soft studio lighting", "magical realism").
* **Verbindungen:**
  * **Input:** Liest `roh_skript.json` aus Service 1.
  * **Output:** Generiert die Datei `finale_prompts.json` (perfekt optimiert für visuelle Viralität).

### 🖼️ Service 3A: Der Bild-Beschaffer (Cloud API Integration)
Der Übergang vom lokalen Denken zur Cloud-Power für hochauflösende Grafiken.

* **Features:**
  * **API-Kommunikation:** Direkte Server-zu-Server-Kommunikation (REST API).
  * **Google Ökosystem:** Nutzt Bild-KI-APIs (z.B. Imagen 4 Fast Vetex AI), um die englischen Prompts blitzschnell und stabil auf externen Großrechnern in fotorealistische Bilder in Größe 9:16 für tiktok/shorts umzuwandeln.
* **Verbindungen:**
  * **Input:** Liest `finale_prompts.json` (spezifisch den Teil `bild_prompt`).
  * **Output:** Speichert durchnummerierte Bilddateien im Output-Ordner.

### 🎙️ Service 3B: Der Ton-Meister (Lokales Text-to-Speech)
Erzeugt die Sprecherstimme offline.

* **Features:**
  * **ElevenLabs Integration:** Nutzt das winzige ElevenLabs-Modell Eleven v3, um natürliche vietnamesische (und deutsche) Stimmen direkt auf dem Orin Nano zu rendern, ohne Cloud-Latenz.
  * **Stimmen:**
    * **Männlich:** Brian - Deep, Resonant and Comforting
    * **Weiblich:** Laura - Calm and Smooth
* **Verbindungen:**
  * **Input:** Liest `finale_prompts.json` (spezifisch den Teil `voiceover_text`).
  * **Output:** Speichert nummerierte Audiodateien im Output-Ordner.

  ### ☁️ Service 4: Der Archiver (Cloud-Upload & Cleanup)
Der finale Schritt, der die Brücke zwischen dem lokalen Edge-Gerät (Jetson) und dem Cloud-Arbeitsplatz schlägt. Er räumt den lokalen Workspace auf und bereitet alles für den endgültigen Videoschnitt vor.

* **Features:**
  * **Markdown-Export (Storyboard):** Erstellt automatisch eine übersichtliche `Storyboard.md` für das spezifische Video. Diese enthält den Titel, die Beschreibung, den vollständigen Sprechertext und alle verwendeten Bild-Prompts für den schnellen Überblick.
  * **Intelligentes Zipping:** Packt alle lokal generierten Assets (hochaufgelöste `.jpg` Bilder, `.wav` Voiceover-Audios, `.json` Skripte) in eine kompakte `.zip` Datei, um Upload-Zeit und Bandbreite zu sparen.
  * **Drive-Automatisierung:** Nutzt die Google Drive API (via Service Account), um völlig autonom einen neuen Projektordner mit aktuellem Zeitstempel im Cloud-Speicher zu erstellen und das ZIP-Paket sowie das Storyboard sicher hochzuladen.
* **Verbindungen:**
  * **Input:** Alle finalen, generierten Dateien aus dem lokalen `output/` Ordner.
  * **Output:** Ein strukturierter Ordner in Google Drive (z.B. `Theodorbot_Archiv/Projekt_2026-04-10_Thema/`), gefüllt mit allen Assets und bereit für den direkten Import in Adobe Premiere.

## 🛠️ Verwendeter Tech-Stack

* **Python 3.10+**: Die Kern-Logik für alle Microservices.
* **Playwright**: Für performantes Headless-Web-Scraping (Service 0).
* **Ollama (Qwen 3.5:4b)**: Lokale LLM-Engine für Text, Logik und Prompt-Generierung. Versteht vietnamesischen und deutschen Kontext perfekt und läuft flüssig auf 8 GB RAM.
* **Piper TTS**: Rasante, offline Text-to-Speech Engine für Voiceovers.
* **Google API**: Stabile Cloud-Anbindung für die Bildgenerierung in Service 3A.

## 🏗️ System-Architektur

Die Pipeline nutzt eine Kombination aus Online-APIs für Trend-Scouting und lokalen, offline laufenden KI-Modellen für die Texterstellung und Sprachgenerierung, um maximale Privatsphäre und Kostenkontrolle zu gewährleisten. Am Ende steht der manuelle Feinschliff in Adobe Premiere.

```text
=============================================================================
                              START (Automatischer Auslöser)
                        Uhrzeit: z.B. Jeden Morgen um 09:00 Uhr
    =============================================================================
                                      │
                                      ▼
    ┌───────────────────────────────────────────────────────────────────────────┐
    │ SERVICE 0: DER TREND-SCOUT (Themenfindung)                                │
    │ Technologie: Python + Playwright + Ollama (Qwen 3.5:4b lokal)             │
    │                                                                           │
    │ Funktion: 1. Liest Schlagzeilen (Webtretho, VnExpress, Dân Trí, etc.).    │
    │           2. Lokale KI wählt das beste, viralste Thema aus.               │
    │           3. Scrapt den kompletten Artikel und generiert Video-Ideen.     │
    │ Output: Eine Textdatei -> 'thema.json' (Titel, Beschreibung, Lösung)      │
    └───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ (Gibt Thema an Service 1)
    ┌───────────────────────────────────────────────────────────────────────────┐
    │ SERVICE 1: THE CREATOR (Lokale Redaktion & Skript)                        │
    │ Technologie: Python + Ollama (Qwen 3.5:4b lokal)                          │
    │                                                                           │
    │ Funktion: Liest 'thema.json'. Schreibt ein warmes Voiceover-Drehbuch.     │
    │           Zerteilt es per Prompt-Chaining in 3- bis 5-Sekunden-Szenen.    │
    │           Übersetzt die Handlung in erste englische Bild-Prompts.         │
    │ Output: Eine strukturierte Datei -> 'roh_skript.json'                     │
    └───────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ (Gibt roh_skript.json an Service 2)
    ┌───────────────────────────────────────────────────────────────────────────┐
    │ SERVICE 2: THE ART DIRECTOR (Bild-Kritiker)                               │
    │ Technologie: Python + Ollama (llama3:8b-instruct-q8_0 lokal)              │
    │                                                                           │
    │ Funktion: Nimmt Bild-Entwürfe aus Service 1. Entfernt "KI-Wörter".        │
    │           Erzwingt Fotorealismus (35mm, film grain, documentary).         │
    │ Output: Eine neue Datei -> 'finale_prompts.json'                          │
    └───────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼ (Liest finale_prompts.json)                   ▼ (Liest Skript-Texte)
    ┌───────────────────────────────────┐   ┌───────────────────────────────────┐
    │ SERVICE 3A: DER BILD-BESCHAFFER   │   │ SERVICE 3B: DER TON-MEISTER       │
    │ Technologie: Python + Google API  │   │ Technologie: Python + Piper TTS   │
    │ (z.B. Imagen via Vertex AI)       │   │                                   │
    │                                   │   │                                   │
    │ Funktion: Sendet saubere Prompts  │   │ Funktion: Wandelt Texte in        │
    │ per API-Call an Google-Server.    │   │ menschliche Audio-Sprache um.     │
    │ Lädt fertige Bilder herunter.     │   │ Lokal und ohne Cloud-Zwang.       │
    │ Output: Szene_01.jpg, etc.        │   │ Output: Szene_01.wav, etc.        │
    └───────────────────────────────────┘   └───────────────────────────────────┘
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      ▼
                                  (Video & Assets bereit)
┌───────────────────────────────────────────────────────────────────────────┐
│ SERVICE 4: DER ARCHIVER (Cloud-Upload & Cleanup)                          │
│ Technologie: Python + Google Drive API                                    │
│                                                                           │
│ Funktion: 1. Erstellt Zusammenfassung als Storyboard.md.                  │
│           2. Zippt alle Bilder, Audios und Skripte.                       │
│           3. Lädt ZIP, Storyboard und das .mp4-Video hoch.                │
│ Output: Upload-Bestätigung & Google Drive Link                            │
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
          3. Nutze die vorbereiteten Prompts aus der .md Datei, um in
            Flow direkt Bilder (Nano Banana) und Videos (Veo 3.1) zu 
            generieren und zusammenzusetzen.