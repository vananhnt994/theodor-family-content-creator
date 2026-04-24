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
TARGET_DURATION_SECONDS = 60        # 1 Minute Gesamtlänge
SCENE_DURATION_MIN = 5              # Minimum 5 Sekunden pro Szene
SCENE_DURATION_MAX = 8              # Maximum 8 Sekunden pro Szene
TARGET_SCENE_COUNT = 10             # ~10 Szenen (realistisch für 60s)

# ---------------------------------------------------------------------------
# System Prompt: Der Redakteur
# ---------------------------------------------------------------------------
# Die KI denkt AUTOMATISCH als professioneller Redakteur und Creator.
# Der System-Prompt wird bei JEDEM Aufruf mitgeschickt.
SYSTEM_PROMPT = f"""Du bist ein einfühlsamer, preisgekrönter Drehbuchautor für emotionale 60-Sekunden-Animationsfilme über {channel_cfg.get('topic', 'den Familienalltag')}.
Deine Aufgabe: Erzähle die Situation und Problematik aus dem übergebenen Thema nachvollziehbar und einfühlsam. Gib im Anschluss die passenden Vorschläge und Ratschläge.
Entscheide basierend auf dem Artikel, ob es wirkungsvoller ist, eine authentische Geschichte aus der Ich-Perspektive (z.B. Mama, Papa oder Kind) zu erfinden, oder als neutraler Erzähler zu berichten. Biete in jedem Fall sanfte Lösungen an.
KEINE harten Aufzählungen oder reinen Theorie-Tipps! Der Text muss wie eine einfühlsame Unterhaltung fließen.

STRIKTE REGELN:
1. Sprache: Das Voiceover (voiceover_text) MUSS auf {channel_cfg.get('language', 'Vietnamesisch')} geschrieben sein.
2. Länge: Das Voiceover muss exakt für ca. 60 Sekunden Laufzeit ausgelegt sein (insgesamt ca. 100 bis 120 Wörter).
3. Szenen: Erstelle exakt 4 bis 6 chronologische visuelle Szenen.
4. Stille (Ma): Das Voiceover darf nicht ununterbrochen durchreden. Füge an emotionalen Stellen mindestens zwei Mal das Tag <break time="2.0s" /> in den {channel_cfg.get('language', 'vietnamesischen')} Text ein, um Pausen zu erzwingen.
5. Hook: Beginne direkt in der Handlung (In medias res) mit einem starken Bild. Keine Begrüßung.
6. Bild-Prompt: Liefere zu jeder Szene eine simple ENGLISCHE Bildbeschreibung. GIB DEN CHARAKTEREN KEINE NAMEN! Nutze Rollen (z.B. "a mother", "a 5-year-old girl").

Halte dich bei der Formatierung exakt an die im jeweiligen Schritt geforderte JSON-Struktur!
"""


# ---------------------------------------------------------------------------
# Voiceover Script Generation Prompt
# ---------------------------------------------------------------------------
VOICEOVER_PROMPT = f"""THEMA FÜR DAS VIDEO:
Titel: {{title}}
Beschreibung: {{description}}
Lösung/Rat: {{solution}}

AUFGABE:
Schreibe ein professionelles Voiceover-Drehbuch für ein {{duration}}-Sekunden-Video (TikTok/YouTube Shorts).

STIMMUNG: Analysiere das Thema und bestimme die passende Grundstimmung.
Die Stimmung muss IMMER ruhig und warm sein – wie eine Gute-Nacht-Geschichte.
Auch bei ernsten Themen: Der Ton bleibt sanft, ermutigend und tröstend.

STORYTELLING-STRUKTUR (in dieser Reihenfolge):
1. EMOTIONALER HOOK (erste 5 Sekunden): Starte mit einer einfühlsamen Frage oder einer Beschreibung, die die emotionale Kernthematik des Artikels trực tiếp. Kein "Hallo" oder "Wusstest du...?"
2. DIE SITUATION (20 Sekunden): Erkläre die Problematik oder Situation aus dem Artikel. Entscheide hierbei dynamisch, ob du die Geschichte aus der Ich-Perspektive eines Betroffenen (z.B. Mama, Papa, Kind) erzählst, um es greifbarer zu machen, oder ob du als neutraler Erzähler berichtest. Der Zuschauer soll sich in jedem Fall verstanden fühlen. WICHTIG: Erfasse die *echte* psychologische oder inhaltliche Tiefe des Themas.
3. VORSCHLÄGE & LÖSUNGEN (25 Sekunden): Teile die *konkreten* Ratschläge und Lösungsansätze *exakt aus dem Artikel*. Erfinde keine flachen, allgemeinen Trostfloskeln. GANZ WICHTIG: Wenn das Thema ein Rätsel, eine mathematische Aufgabe oder eine spezifische Geschichte ist (z.B. 17 Kamele aufteilen), MUSS die genaue Lösung (die konkreten Rechenschritte oder logischen Schritte) zwingend und verständlich im Voiceover erklärt werden! Präsentiere die Vorschläge fließend im Text.
4. WARME BOTSCHAFT (10 Sekunden): Ende mit einer tröstenden, ermutigenden Botschaft, die Kraft gibt, basierend auf dem echten Artikel-Fazit. Kein hartes Belehren.

STIL-REGELN:
- Schreibe so, als würde eine ruhige, warme Stimme eine Geschichte am Lagerfeuer erzählen
- KEINE Listen, KEINE Aufzählungen, KEINE Tipps-Formate
- Nur fließender, emotionaler Erzähltext
- Verwende kurze, poetische Sätze mit viel Gefühl
- Füge mindestens 2x das Tag <break time="2.0s" /> an emotionalen Stellen ein

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{{{
  "mood": "<stimmung des videos, z.B.: warm und nachdenklich>",
  "voiceover_full": "<der komplette Voiceover-Text als ein zusammenhängender Text, auf {channel_cfg.get('language', 'Vietnamesisch')}, ca. {{duration}} Sekunden gesprochen>",
  "seo": {{{{
    "title": "<Ein klickstarker, neugierig machender Titel auf {channel_cfg.get('language', 'Vietnamesisch')}, max. 60 Zeichen>",
    "description": "<SEO-optimierte Videobeschreibung. Erste zwei Sätze mit den wichtigsten Suchbegriffen>",
    "hashtags": "<Exakt 5 spitze Hashtags auf {channel_cfg.get('language', 'Vietnamesisch')}, durch Leerzeichen getrennt>"
  }}}}
}}}}"""


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
3. "emotion": Die Emotion dieser Szene (z.B. "peaceful", "warm", "gentle", "hopeful", "serene")
4. "draft_prompt": Ein englischer Bild-Prompt für ein passendes Bild. WICHTIG für Bild-Stil und Konsistenz:
   - CHARACTER CONSISTENCY: Lege für Charaktere GANZ GENAUE, feste visuelle Eigenschaften fest (Rolle, Alter, Kleidung, Kleiderfarbe, Frisur). GIB DEN CHARAKTEREN KEINE NAMEN (verwende stattdessen "a mother", "a father", "a 5-year-old girl", "a teacher"). Verwende EXAKT DIESELBE detaillierte Beschreibung (z.B. "a 5-year-old Vietnamese girl with short black hair wearing a pink dress") in JEDEM Prompt, in dem diese Person auftaucht! Erwähne auch in Detailaufnahmen IMMER den Charakter und das Outfit (z.B. statt nur "Button" schreibe "The button on the pink dress of a 5-year-old girl...").
   - AVOID MATH & NUMBERS: KI-Bildgeneratoren können nicht zählen oder rechnen. Fordere NIEMALS "17 Kamele" oder "3 Wege" oder "eine Rechenaufgabe" auf einem Bild an. Beschreibe stattdessen simple visuelle Metaphern oder einfache Charakter-Porträts (z.B. "a few camels", "the sons looking amazed", "a single lightbulb").
   - ALL scenes MUST be in flat 2D Studio Ghibli anime style. Do NOT use realistic or photographic styles.
   - BACKGROUNDS must be SIMPLE and MINIMAL: soft pastel colors, gentle gradients, or simple nature elements. NO busy or detailed environments.
   - MOOD: Every scene must radiate calm, peace, and serenity. Warm sunset tones, soft golden light, gentle breeze.
   - Warme Farbtöne, weiches Licht, natürliche Atmosphäre.

STIMMUNG DES VIDEOS: {{mood}}

Trả lời CHỈ bằng JSON, KHÔNG thêm text nào khác:
{{{{
  "scenes": [
    {{{{
      "scene_number": 1,
      "voiceover_text": "...",
      "duration_seconds": 5,
      "emotion": "...",
      "draft_prompt": "..."
    }}}}
  ]
}}}}"""
