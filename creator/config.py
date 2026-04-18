"""
Configuration for Service 1: The Creator.
System prompts, model settings, and output paths.
"""

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from channel_config import load_channel_config

channel_cfg = load_channel_config()

GEMINI_MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Input / Output
# ---------------------------------------------------------------------------
INPUT_DIR = "output"
INPUT_FILENAME = "thema.json"
OUTPUT_DIR = "output"
OUTPUT_FILENAME = "roh_skript.json"

# ---------------------------------------------------------------------------
# Video Constraints
# ---------------------------------------------------------------------------
TARGET_DURATION_SECONDS = 90       # 1,5 Minuten Gesamtlänge
SCENE_DURATION_MIN = 5             # Minimum 5 Sekunden pro Szene
SCENE_DURATION_MAX = 8             # Maximum 8 Sekunden pro Szene
TARGET_SCENE_COUNT = 15            # ~15 Szenen (realistisch für 90s)

# ---------------------------------------------------------------------------
# System Prompt: Der Redakteur
# ---------------------------------------------------------------------------
# Die KI denkt AUTOMATISCH als professioneller Redakteur und Creator.
# Der System-Prompt wird bei JEDEM Aufruf mitgeschickt.
SYSTEM_PROMPT = f"""Du bist ein preisgekrönter Drehbuchautor für emotionale 90-Sekunden-Animationsfilme über {channel_cfg.get('topic', 'den Familienalltag')}.
Deine Aufgabe: Erfinde zu dem übergebenen Thema eine konkrete, rührende Situation mit Charakteren.
KEINE Listen, KEINE reinen Theorie-Tipps! Zeige eine Handlung.

STRIKTE REGELN:
1. Sprache: Das Voiceover (voiceover_text) MUSS auf {channel_cfg.get('language', 'Vietnamesisch')} geschrieben sein.
2. Länge: Das Voiceover muss exakt für ca. 90 Sekunden Laufzeit ausgelegt sein (insgesamt ca. 150 bis 180 Wörter).
3. Szenen: Erstelle exakt 6 bis 8 chronologische visuelle Szenen.
4. Stille (Ma): Das Voiceover darf nicht ununterbrochen durchreden. Füge an emotionalen Stellen mindestens drei Mal das Tag <break time="2.0s" /> in den {channel_cfg.get('language', 'vietnamesischen')} Text ein, um Pausen zu erzwingen.
5. Hook: Beginne direkt in der Handlung (In medias res) mit einem starken Bild. Keine Begrüßung.
6. Bild-Prompt: Liefere zu jeder Szene eine simple ENGLISCHE Bildbeschreibung. Benenne die Charaktere darin.

Halte dich bei der Formatierung exakt an die im jeweiligen Schritt geforderte JSON-Struktur!
"""


# ---------------------------------------------------------------------------
# Voiceover Script Generation Prompt
# ---------------------------------------------------------------------------
VOICEOVER_PROMPT = f"""THEMA FÜR DAS VIDEO:
Titel: {{title}}
Beschreibung: {{description}}
Lösung/Rat: {{solution}}

STIMMUNG DES THEMAS: Analysiere das Thema und bestimme die passende Stimmung (z.B. warm, nachdenklich, fröhlich, ermutigend, melancholisch).

AUFGABE:
Schreibe ein professionelles Voiceover-Drehbuch für ein {{duration}}-Sekunden-Video (TikTok/YouTube Shorts).

ANFORDERUNGEN:
1. Schreibe das Drehbuch als EINEN zusammenhängenden Voiceover-Text (ca. {{duration}} Sekunden gesprochen)
2. Der Text soll sich so anfühlen, als würde ein Freund die Geschichte erzählen
3. Starte mit einem emotionalen Hook in den ersten 3 Sekunden
4. Baue die Geschichte auf: Situation → Gefühl → Erkenntnis → Botschaft
5. Ende mit einem starken Moment

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{
  "mood": "<stimmung des videos, z.B.: warm und nachdenklich>",
  "voiceover_full": "<der komplette Voiceover-Text als ein zusammenhängender Text, auf {channel_cfg.get('language', 'Vietnamesisch')}, ca. {{duration}} Sekunden gesprochen>",
  "seo": {{
    "title": "<Ein klickstarker, neugierig machender Titel auf {channel_cfg.get('language', 'Vietnamesisch')}, max. 60 Zeichen>",
    "description": "<SEO-optimierte Videobeschreibung. Erste hai Sätze mit den wichtigsten Suchbegriffen>",
    "hashtags": "<Exakt 5 spitze, Hashtags auf {channel_cfg.get('language', 'Vietnamesisch')}, durch Leerzeichen getrennt>"
  }}
}}"""


# ---------------------------------------------------------------------------
# Scene Splitting Prompt
# ---------------------------------------------------------------------------
SCENE_SPLIT_PROMPT = f"""VOICEOVER-TEXT:
{{voiceover}}

AUFGABE:
Teile diesen Voiceover-Text in genau {{scene_count}} Szenen auf. Jede Szene ist {{min_sec}}-{{max_sec}} Sekunden lang.

Für JEDE Szene:
1. "voiceover_text": Der exakte Teil des Voiceover-Textes für diese Szene
2. "duration_seconds": Geschätzte Sprechdauer (zwischen {{min_sec}} und {{max_sec}} Sekunden)
3. "emotion": Die Emotion dieser Szene (z.B. "curious", "melancholic", "hopeful", "warm", "playful")
4. "draft_prompt": Ein englischer Bild-Prompt für ein passendes Bild. WICHTIG für Bild-Stil und Konsistenz:
   - CHARACTER CONSISTENCY: Lege für Charaktere GANZ GENAUE, feste visuelle Eigenschaften fest (Alter, Kleidung, Kleiderfarbe, Frisur). Verwende EXAKT DIESELBE Beschreibung in JEDEM Prompt, in dem diese Person auftaucht! Ohne diese Regel wechselt die KI sonst das Aussehen in jedem Bild.
   - Bevorzuge süße, realistische, authentische Szenen und halte den Hintergrund detailliert.
   - Manchmal darf es auch im sanften Ghibli/Aquarell-Stil sein, wenn die Stimmung es verlangt.
   - NIEMALS: übertrieben fancy, künstlich perfekt, oder unrealistisch.
   - Warme Farbtöne, weiches Licht, natürliche Atmosphäre.

STIMMUNG DES VIDEOS: {{mood}}

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "voiceover_text": "...",
      "duration_seconds": 5,
      "emotion": "...",
      "draft_prompt": "..."
    }}
  ]
}}"""
