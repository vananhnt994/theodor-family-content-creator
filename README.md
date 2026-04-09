# 🎬 Theodorbot: The Local Video Content Factory

Eine vollautomatisierte, ressourcenschonende Microservice-Pipeline zur Erstellung von Kurzvideos (TikToks, YouTube Shorts). 
Optimiert für Edge-Geräte mit begrenztem Arbeitsspeicher (z.B. 8 GB RAM), da alle Services strikt nacheinander ausgeführt werden.

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
