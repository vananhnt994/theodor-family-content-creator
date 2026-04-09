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
Der kreative Motor des Systems. Arbeitet zu 100 % lokal auf dem Jetson.

* **Features:**
  * **Skript-Erstellung:** Schreibt ein warmes Voiceover-Drehbuch auf Basis des ermittelten Themas.
  * **Szenen-Splitting:** Teilt den Text logisch in 3- bis 5-Sekunden-Abschnitte auf, die ideal für Kurzvideos sind.
  * **Prompt-Drafting:** Übersetzt die Handlung jeder Szene in erste englische Bild-Prompts.
* **Verbindungen:**
  * **Input:** Liest `thema.json` aus Service 0.
  * **Output:** Generiert die Datei `roh_skript.json` (enthält Array aus Szenen mit `voiceover_text` und `draft_prompt`).

### 🧐 Service 2: The Art Director (Die Qualitätskontrolle)
Der Wächter über den visuellen Stil. Verhindert, dass Bilder nach billiger KI aussehen.

* **Features:**
  * **Prompt-Sanitization:** Löscht rigoros Standard-KI-Vokabular (wie "epic", "cinematic", "masterpiece").
  * **Style-Enforcement:** Reichert die Prompts mit festen Fotografen-Regeln an (z.B. "shot on 35mm film", "natural documentary lighting", "subtle film grain").
* **Verbindungen:**
  * **Input:** Liest `roh_skript.json` aus Service 1.
  * **Output:** Generiert die Datei `finale_prompts.json` (die saubere Bauanleitung für die nächsten Schritte).

### 🖼️ Service 3A: Der Bild-Beschaffer (Adobe Automation)
Der technische "Hack", um vorhandene Adobe-Credits ohne Enterprise-API zu nutzen.

* **Features:**
  * **Browser-Fernsteuerung:** Startet Playwright mit gespeichertem User-Profil (Cookies), um den Login-Prozess bei Adobe Firefly zu umgehen.
  * **Auto-Typing & Download:** Fügt die Prompts iterativ in das Textfeld ein, wartet auf die Generierung und speichert das Ergebnis lokal ab.
* **Verbindungen:**
  * **Input:** Liest `finale_prompts.json` (spezifisch den Teil `bild_prompt`).
  * **Output:** Speichert durchnummerierte Bilddateien (z.B. `szene_01.jpg`, `szene_02.jpg`) im Projektordner.

### 🎙️ Service 3B: Der Ton-Meister (Lokales Text-to-Speech)
Erzeugt die Sprecherstimme offline und rasend schnell.

* **Features:**
  * **Piper TTS Integration:** Nutzt das winzige Piper-Modell, um natürliche vietnamesische Stimmen direkt auf dem Orin Nano zu rendern, ohne Cloud-Latenz oder Kosten.
* **Verbindungen:**
  * **Input:** Liest `finale_prompts.json` (spezifisch den Teil `voiceover_text`).
  * **Output:** Speichert nummerierte Audiodateien (z.B. `szene_01.wav`, `szene_02.wav`) im Projektordner.

## 🛠️ Verwendeter Tech-Stack

* **Python 3.10+**: Die Kern-Logik für alle Microservices.
* **Playwright**: Für Web-Scraping (Service 0) und Browser-Automatisierung von Adobe Firefly (Service 3A).
* **Ollama (Llama 3.2 - 3B)**: Lokale LLM-Engine für Text- und Prompt-Generierung. Ideal für Systeme mit limitiertem RAM.
* **Piper TTS**: Rasante, offline Text-to-Speech Engine für Voiceovers.
* **Gemini API (Free Tier)**: Für fortgeschrittene Text- und Trend-Analysen ausgelesener Webseiten.

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
│ Technologie: Python + Playwright + Online-KI-API (z.B. Gemini Pro)        │
│                                                                           │
│ Funktion: 1. Playwright liest Text-Schlagzeilen von Reddit/News-Seiten.   │
│           2. Sendet Liste an KI-API zur Themen-Analyse.                   │
│           3. KI wählt das beste, witzigste Thema aus.                     │
│ Output: Eine Textdatei -> 'thema.json' (z.B. "Die erste Fahrstunde")      │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (Gibt Thema an Service 1)
┌───────────────────────────────────────────────────────────────────────────┐
│ SERVICE 1: THE CREATOR (Lokale Redaktion & Skript)                        │
│ Technologie: Python + Ollama (Llama 3.2 - 3B Modell)                      │
│                                                                           │
│ Funktion: Liest 'thema.json'. Schreibt Voiceover-Skript.                  │
│           Zerteilt es in Szenen. Schreibt erste Bild-Entwürfe.            │
│ Output: Eine strukturierte Datei -> 'roh_skript.json'                     │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ (Gibt roh_skript.json an Service 2)
┌───────────────────────────────────────────────────────────────────────────┐
│ SERVICE 2: THE ART DIRECTOR (Bild-Kritiker)                               │
│ Technologie: Python + Ollama (Llama 3.2 mit strengem System-Prompt)       │
│                                                                           │
│ Funktion: Nimmt die Bild-Entwürfe aus Service 1. Entfernt "KI-Wörter"     │
│           (epic, perfect). Erzwingt Fotorealismus (35mm, film grain).     │
│ Output: Eine neue Datei -> 'finale_prompts.json'                          │
└───────────────────────────────────────────────────────────────────────────┘
                                  │
          ┌───────────────────────┴───────────────────────┐
          ▼ (Liest finale_prompts.json)                   ▼ (Liest Skript-Texte)
┌───────────────────────────────────┐   ┌───────────────────────────────────┐
│ SERVICE 3A: DER BILD-BESCHAFFER   │   │ SERVICE 3B: DER TON-MEISTER       │
│ Technologie: Python + Playwright  │   │ Technologie: Python + Piper TTS   │
│                                   │   │                                   │
│ Funktion: Steuert unsichtbar den  │   │ Funktion: Wandelt deutsche Texte  │
│ Browser. Ruft Adobe Firefly auf.  │   │ in menschliche Audio-Sprache um.  │
│ Tippt Prompts und lädt Bilder.    │   │ Lokal und ohne Cloud-Zwang.       │
│ Output: Szene_01.jpg, etc.        │   │ Output: Szene_01.wav, etc.        │
└───────────────────────────────────┘   └───────────────────────────────────┘
          │                                               │
          └───────────────────────┬───────────────────────┘
                                  ▼
=============================================================================
                          ZIEL (Arbeitsplatz)
            Ordner: "/Desktop/Theodorbot/Projekt_xyz/"
            Gefüllt mit perfekten .jpg Bildern und .wav Dateien.
=============================================================================
                                  │
                                  ▼
                        ADOBE PREMIERE (Human-in-the-Loop)
             Manuelle Regie: Dateien in die Timeline ziehen,
             Übergänge anpassen und finalen Schnitt exportieren.
